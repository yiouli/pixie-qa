"""pixie.instrumentation.wrap — data-oriented observation and wrapping API.

Combines all wrap-related functionality:
- ``wrap()`` — data-oriented observation API for dependency injection and output capture
- ``WrappedData`` / ``WrapLogEntry`` — Pydantic model for wrap data and JSONL loading
- Context-variable registries for eval mode (eval_input / eval_output)
- Serialization helpers using jsonpickle
- OTel log-record processors for wrap events (TraceLogProcessor, EvalCaptureLogProcessor)
"""

from __future__ import annotations

import functools
import json
import threading
from collections.abc import Callable, Mapping
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Literal, TypeVar

import jsonpickle
from opentelemetry.sdk._logs import LoggerProvider, LogRecordProcessor, ReadWriteLogRecord
from pydantic import BaseModel, ConfigDict, JsonValue

from pixie.instrumentation.models import ENTRY_KWARGS_KEY

T = TypeVar("T")


# ── Wrap data model ──────────────────────────────────────────────────────────


Purpose = Literal["input", "output", "state"]


class WrappedData(BaseModel):
    """A single ``wrap()`` observation record.

    Used in three contexts:

    1. **Trace files** — written to JSONL by the trace writer.
    2. **Dataset ``eval_input``** — each dataset item stores its input
       as ``list[WrappedData]`` (JSON-serialized).
    3. **In-memory emission** — created by ``wrap()`` before dispatching.

    Attributes:
        type: Always ``"wrap"`` for wrap events.
        name: The wrap point name (matches ``wrap(name=...)``).
        purpose: One of `"input"``, ``"output"``, ``"state"``.
        data: The observed data value (stored as JSON-compatible value).
        description: Optional human-readable description.
        trace_id: OTel trace ID (if available).
        span_id: OTel span ID (if available).
    """

    type: str = "wrap"
    name: str
    purpose: Purpose
    data: JsonValue
    description: str | None = None
    trace_id: str | None = None
    span_id: str | None = None

    # Keep wrap records immutable after validation to avoid accidental mutation.
    model_config = ConfigDict(frozen=True)


def filter_by_purpose(
    entries: list[WrappedData],
    purposes: set[str],
) -> list[WrappedData]:
    """Filter wrap log entries by purpose.

    Args:
        entries: List of wrap data entries.
        purposes: Set of purpose values to include.

    Returns:
        Filtered list.
    """
    return [e for e in entries if e.purpose in purposes]


# ── Serialization helpers ─────────────────────────────────────────────────────


def serialize_wrap_data(data: Any) -> JsonValue:
    """Serialize a Python object to a JSON-compatible value.

    Uses jsonpickle internally to preserve type information (e.g.
    ``py/object`` keys) and returns a parsed JSON value (dict, list,
    string, etc.) — **not** a raw JSON string.

    :func:`deserialize_wrap_data` can reconstruct the original Python
    object from the returned value.
    """
    encoded: str = jsonpickle.encode(data, unpicklable=True)  # pyright: ignore[reportAssignmentType]
    return json.loads(encoded)  # type: ignore[no-any-return]


def deserialize_wrap_data(data: JsonValue) -> Any:
    """Deserialize a JSON-compatible value back to a Python object."""
    return jsonpickle.decode(json.dumps(data))


# ── Context-variable registries ──────────────────────────────────────────────


# Input registry: populated by test runner before each eval run.
# Keys are wrap names, values are JSON-compatible objects.
_eval_input: ContextVar[Mapping[str, JsonValue] | None] = ContextVar("_eval_input", default=None)

# Output list: each dict is the body of a wrap event (output/state).
_eval_output: ContextVar[list[dict[str, Any]] | None] = ContextVar("_eval_output", default=None)


def set_eval_input(registry: Mapping[str, JsonValue]) -> None:
    """Set the eval input registry for the current context."""
    _eval_input.set(registry)


def get_eval_input() -> Mapping[str, JsonValue] | None:
    """Get the eval input registry, or ``None`` if not in eval mode."""
    return _eval_input.get()


def clear_eval_input() -> None:
    """Clear the eval input registry."""
    _eval_input.set(None)


def init_eval_output() -> list[dict[str, Any]]:
    """Initialise and return a fresh eval output list."""
    out: list[dict[str, Any]] = []
    _eval_output.set(out)
    return out


def get_eval_output() -> list[dict[str, Any]] | None:
    """Get the eval output list, or ``None`` if not initialised."""
    return _eval_output.get()


def clear_eval_output() -> None:
    """Clear the eval output list."""
    _eval_output.set(None)


# ── OTel log-record processors ──────────────────────────────────────────────

# Module-level trace log processor reference, set by the trace command.
_trace_log_processor: TraceLogProcessor | None = None

# Guard: has an EvalCaptureLogProcessor been registered?
_eval_capture_registered = False


def get_trace_log_processor() -> TraceLogProcessor | None:
    """Return the active :class:`TraceLogProcessor`, or ``None``."""
    return _trace_log_processor


def set_trace_log_processor(processor: TraceLogProcessor | None) -> None:
    """Set the active :class:`TraceLogProcessor`."""
    global _trace_log_processor  # noqa: PLW0603
    _trace_log_processor = processor


class WrapNameCollisionError(ValueError):
    """Raised when a wrap name collides with a reserved key or duplicate."""


class TraceLogProcessor(LogRecordProcessor):
    """Write wrap event bodies as JSON lines to a file.

    Validates wrap names during tracing: raises :class:`WrapNameCollisionError`
    when a wrap name collides with the reserved ``ENTRY_KWARGS_KEY`` or with
    a name already seen in the current trace.

    Args:
        output_path: Path to the JSONL trace file.  Parent directories
            are created if missing; the file is truncated on init.
    """

    def __init__(self, output_path: str) -> None:
        self._path = Path(output_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._path.write_text("")
        self._seen_names: set[str] = set()

    def _validate_wrap_name(self, name: str) -> None:
        """Raise :class:`WrapNameCollisionError` on name conflicts."""
        if name == ENTRY_KWARGS_KEY:
            raise WrapNameCollisionError(
                f"wrap(name={name!r}) collides with the reserved key "
                f"{ENTRY_KWARGS_KEY!r} used for entry kwargs in eval_input. "
                f"Choose a different name for this wrap point."
            )
        if name in self._seen_names:
            raise WrapNameCollisionError(
                f"wrap(name={name!r}) was already used in this trace. "
                f"Each wrap point must have a unique name."
            )
        self._seen_names.add(name)

    def on_emit(self, log_record: ReadWriteLogRecord) -> None:  # noqa: D102
        body = log_record.log_record.body
        if not isinstance(body, dict):
            return
        # Validate wrap names before writing
        if body.get("type") == "wrap":
            name = body.get("name")
            if isinstance(name, str):
                self._validate_wrap_name(name)
        line = json.dumps(body, default=str)
        with self._lock, open(self._path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def shutdown(self) -> None:  # noqa: D102
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:  # noqa: D102
        return True

    def write_line(self, record: dict[str, Any]) -> None:
        """Write an arbitrary JSON record (e.g. kwargs, llm_span)."""
        line = json.dumps(record, default=str)
        with self._lock, open(self._path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


class EvalCaptureLogProcessor(LogRecordProcessor):
    """Append wrap event bodies to the ``eval_output`` context variable.

    Only events with ``purpose="output"`` or ``purpose="state"`` are
    captured.  The processor is a no-op when ``eval_output`` has not been
    initialised (i.e. outside of an eval run).
    """

    def on_emit(self, log_record: ReadWriteLogRecord) -> None:  # noqa: D102
        body = log_record.log_record.body
        if not isinstance(body, dict):
            return

        purpose = body.get("purpose")
        if purpose not in ("output", "state"):
            return

        eval_output = get_eval_output()
        if eval_output is not None:
            eval_output.append(body)

    def shutdown(self) -> None:  # noqa: D102
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:  # noqa: D102
        return True


# ── wrap() API ───────────────────────────────────────────────────────────────

logger_provider = LoggerProvider()
_logger = logger_provider.get_logger(__name__)


class WrapRegistryMissError(KeyError):
    """Raised when a wrap(purpose="input") name is not found in the eval registry."""

    def __init__(self, name: str) -> None:
        super().__init__(
            f"wrap(name={name!r}, purpose='input') not found in eval registry. "
            f"Ensure the dataset entry has a value for {name!r} in its input data."
        )
        self.name = name


class WrapTypeMismatchError(TypeError):
    """Raised when deserialized registry value doesn't match expected type."""

    def __init__(self, name: str, expected_type: type, actual_type: type) -> None:
        super().__init__(
            f"wrap(name={name!r}): expected type {expected_type.__name__}, "
            f"got {actual_type.__name__} from registry."
        )
        self.name = name


def _emit_and_return(data: T, name: str, purpose: Purpose, description: str | None) -> T:

    def _emit(val: Any) -> None:
        _logger.emit(
            body=WrappedData(
                name=name,
                purpose=purpose,
                data=serialize_wrap_data(val),
                description=description,
            ).model_dump(mode="json")
        )

    if callable(data):
        original_callable: Callable[..., Any] = data  # type: ignore[assignment,unused-ignore]

        @functools.wraps(original_callable)
        def _capturing_callable(*args: Any, **kwargs: Any) -> Any:
            result = original_callable(*args, **kwargs)
            _emit(result)
            return result

        return _capturing_callable  # type: ignore[return-value]
    else:
        _emit(data)
        return data


def wrap(
    data: T,
    *,
    purpose: Purpose,
    name: str,
    description: str | None = None,
) -> T:
    """Observe *data* at a named wrap point with a specified purpose."""
    is_callable = callable(data)

    input_registry = get_eval_input()

    if input_registry is not None and purpose == "input":
        if name not in input_registry:
            raise WrapRegistryMissError(name)
        deserialized = deserialize_wrap_data(input_registry[name])
        serialized_value = input_registry[name]

        def _emit_injected() -> None:
            """Emit the injected value so trace log processors see it."""
            _logger.emit(
                body=WrappedData(
                    name=name,
                    purpose=purpose,
                    data=serialized_value,
                    description=description,
                ).model_dump(mode="json")
            )

        if is_callable:
            # Return a callable that emits and returns the injected value.
            # Parameters are intentionally ignored — eval mode replaces
            # the original function's computation with the registry value.
            def _injected_callable(*args: Any, **kwargs: Any) -> Any:
                _emit_injected()
                return deserialized

            return _injected_callable  # type: ignore[return-value]
        _emit_injected()
        return deserialized  # type: ignore[no-any-return]
    else:
        return _emit_and_return(data, name, purpose, description)


def ensure_eval_capture_registered() -> None:
    """Register a single :class:`EvalCaptureLogProcessor` on the wrap logger.

    Safe to call multiple times — only the first call has an effect.
    """
    global _eval_capture_registered  # noqa: PLW0603
    if _eval_capture_registered:
        return
    logger_provider.add_log_record_processor(EvalCaptureLogProcessor())
    _eval_capture_registered = True
