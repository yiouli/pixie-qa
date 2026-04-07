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
from collections.abc import Callable
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Literal, TypeVar

import jsonpickle
from opentelemetry.sdk._logs import LogRecordProcessor, LoggerProvider, ReadWriteLogRecord
from pydantic import BaseModel

T = TypeVar("T")


# ── Wrap data model ──────────────────────────────────────────────────────────


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
        purpose: One of ``"entry"``, ``"input"``, ``"output"``, ``"state"``.
        data: The observed data value (stored as JSON-compatible value).
        description: Optional human-readable description.
        trace_id: OTel trace ID (if available).
        span_id: OTel span ID (if available).
    """

    type: str = "wrap"
    name: str
    purpose: str
    data: Any
    description: str | None = None
    trace_id: str | None = None
    span_id: str | None = None


# Backward-compatible alias
WrapLogEntry = WrappedData


def parse_wrapped_data_list(raw: Any) -> list[WrappedData]:
    """Parse a JSON value into a list of :class:`WrappedData`.

    Validates that *raw* is a list of dicts, each with at least
    ``purpose`` and ``name`` keys, and returns validated models.

    Args:
        raw: A JSON-compatible value (typically from ``eval_input``).

    Returns:
        List of validated :class:`WrappedData` objects.

    Raises:
        ValueError: If *raw* is not a list or any item is malformed.
    """
    if not isinstance(raw, list):
        raise ValueError(
            f"Expected eval_input to be a list of WrappedData objects, "
            f"got {type(raw).__name__}. "
            f"Use 'pixie trace filter --purpose entry,input' output as the template."
        )
    result: list[WrappedData] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(
                f"eval_input[{i}]: expected a WrappedData object (dict), "
                f"got {type(item).__name__}."
            )
        if "purpose" not in item or "name" not in item:
            raise ValueError(
                f"eval_input[{i}]: missing required 'purpose' and/or 'name' fields. "
                f"Each eval_input item must be a WrappedData object with "
                f"type, name, purpose, and data fields."
            )
        result.append(WrappedData.model_validate(item))
    return result


def load_wrap_log_entries(jsonl_path: str | Path) -> list[WrappedData]:
    """Load all wrap log entries from a JSONL file.

    Skips non-wrap lines (e.g. ``type=llm_span``) and malformed lines.

    Args:
        jsonl_path: Path to a JSONL trace file.

    Returns:
        List of :class:`WrappedData` objects.
    """
    entries: list[WrappedData] = []
    path = Path(jsonl_path)
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("type") != "wrap":
                continue
            try:
                entries.append(WrappedData.model_validate(record))
            except Exception:
                continue
    return entries


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


def serialize_wrap_data(data: Any) -> str:
    """Serialize a Python object to a jsonpickle JSON string.

    The output is valid JSON but uses jsonpickle's type-metadata format
    (e.g. ``py/object`` keys) rather than plain JSON. This preserves type
    information so that :func:`deserialize_wrap_data` can reconstruct the
    original Python object.
    """
    return jsonpickle.encode(data, unpicklable=True, indent=2)  # type: ignore[no-any-return]


def deserialize_wrap_data(data_str: str) -> Any:
    """Deserialize a jsonpickle string back to a Python object."""
    return jsonpickle.decode(data_str)


# ── Context-variable registries ──────────────────────────────────────────────


# Input registry: populated by test runner before each eval run.
# Keys are wrap names, values are jsonpickle-serialised strings.
_eval_input: ContextVar[dict[str, str] | None] = ContextVar(
    "_eval_input", default=None
)

# Output list: each dict is the body of a wrap event (output/state).
_eval_output: ContextVar[list[dict[str, Any]] | None] = ContextVar(
    "_eval_output", default=None
)


def set_eval_input(registry: dict[str, str]) -> None:
    """Set the eval input registry for the current context."""
    _eval_input.set(registry)


def get_eval_input() -> dict[str, str] | None:
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


class TraceLogProcessor(LogRecordProcessor):
    """Write wrap event bodies as JSON lines to a file.

    Args:
        output_path: Path to the JSONL trace file.  Parent directories
            are created if missing; the file is truncated on init.
    """

    def __init__(self, output_path: str) -> None:
        self._path = Path(output_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._path.write_text("")

    def on_emit(self, log_record: ReadWriteLogRecord) -> None:  # noqa: D102
        body = log_record.log_record.body
        if not isinstance(body, dict):
            return
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


def _emit_and_return(data: T, name: str, purpose: str, description: str | None) -> T:

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
    purpose: Literal["entry", "input", "output", "state"],
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
        if is_callable:
            # Return a callable that always returns the injected value.
            # Parameters are intentionally ignored — eval mode replaces
            # the original function's computation with the registry value.
            def _injected_callable(*args: Any, **kwargs: Any) -> Any:
                return deserialized

            return _injected_callable  # type: ignore[return-value]
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
