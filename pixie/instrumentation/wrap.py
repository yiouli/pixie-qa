"""``pixie.wrap`` — data-oriented observation API.

``wrap()`` observes a data value or callable at a named point in the
processing pipeline.  Its behavior depends on the active mode:

- **No-op** (tracing disabled, no eval registry): returns ``data`` unchanged.
- **Tracing** (``PIXIE_TRACING=1``): writes to the trace file and emits an
  OTel event (via span event if a span is active, or via OTel logger
  otherwise) and returns ``data`` unchanged (or wraps a callable so the
  event fires on call).
- **Eval** (eval registry active): injects dependency data for
  ``purpose="input"``, captures output/state for ``purpose="output"``/
  ``purpose="state"``.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import Any, Literal, TypeVar

from opentelemetry import trace

from pixie.config import get_config

from .wrap_registry import (
    get_capture_registry,
    get_input_registry,
    get_output_capture_registry,
    get_state_capture_registry,
)
from .wrap_serialization import deserialize_wrap_data, serialize_wrap_data

T = TypeVar("T")

_logger = logging.getLogger("pixie.wrap")


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


def _emit_wrap_event(
    name: str,
    purpose: str,
    data_serialized: str,
    description: str | None,
) -> None:
    """Emit an OTel event for a wrap observation.

    If a recording span is active, adds the event to that span.
    Otherwise, emits via the Python logger.  When OpenTelemetry log
    exporters are configured, the logger output is captured as OTel log
    records; without exporters it falls through to standard Python logging.
    """
    span = trace.get_current_span()
    attrs = {
        "wrap.name": name,
        "wrap.purpose": purpose,
        "wrap.data": data_serialized,
        **({"wrap.description": description} if description else {}),
    }
    if span.is_recording():
        span.add_event("pixie.wrap", attributes=attrs)
    else:
        # No active span — use Python logger so the event is still observable.
        # OTel log exporters will capture this if configured; otherwise it
        # goes to the standard logging output.
        _logger.info(
            "pixie.wrap: %s (purpose=%s)",
            name,
            purpose,
            extra={"wrap_attributes": attrs},
        )


def wrap(
    data: T,
    *,
    purpose: Literal["entry", "input", "output", "state"],
    name: str,
    description: str | None = None,
) -> T:
    """Observe a data value or data-provider callable at a point in the processing pipeline.

    ``data`` can be either a plain value or a callable that produces a value.
    In both cases the return type is ``T`` — the caller gets back exactly the
    same type it passed in when in no-op or tracing modes.

    In eval mode with ``purpose="input"``, the returned value (or callable) is
    replaced with the deserialized registry value.  When ``data`` is callable
    the returned wrapper ignores the original function and returns the injected
    value on every call; in all other modes the returned callable wraps the
    original and adds tracing or capture behaviour.

    Args:
        data: A data value or a data-provider callable.
        purpose: Classification of the data point:
            - "entry": app input via entry point (user message, request body)
            - "input": data from external dependencies (DB records, API responses)
            - "output": data going out to external systems or users
            - "state": intermediate state for evaluation (routing decisions, etc.)
        name: Unique identifier for this data point. Used as the key in the
            eval registry and in trace logs.
        description: Optional human-readable description of what this data is.

    Returns:
        The original data unchanged (tracing / no-op modes), or the
        registry value (eval mode with purpose="input").  When ``data``
        is callable the return value is also callable.
    """
    is_callable = callable(data)
    input_registry = get_input_registry()
    in_eval_mode = input_registry is not None

    # ── Eval mode ────────────────────────────────────────────────────────────
    if in_eval_mode:
        assert input_registry is not None  # narrow type for mypy
        if purpose == "input":
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

        elif purpose in ("output", "state"):
            # Capture to the appropriate registry
            capture_reg = get_capture_registry()
            purpose_reg = (
                get_output_capture_registry()
                if purpose == "output"
                else get_state_capture_registry()
            )
            if is_callable:
                original_callable: Callable[..., Any] = data  # type: ignore[assignment]

                @functools.wraps(original_callable)
                def _capturing_callable(*args: Any, **kwargs: Any) -> Any:
                    result = original_callable(*args, **kwargs)
                    if capture_reg is not None:
                        capture_reg[name] = result
                    if purpose_reg is not None:
                        purpose_reg[name] = result
                    return result

                return _capturing_callable  # type: ignore[return-value]
            else:
                if capture_reg is not None:
                    capture_reg[name] = data
                if purpose_reg is not None:
                    purpose_reg[name] = data
                return data

        else:
            # purpose == "entry": behave like no-op in eval mode
            return data

    # ── Tracing mode ─────────────────────────────────────────────────────────
    config = get_config()
    if config.tracing_enabled:
        # Lazy import to avoid circular dependency
        from pixie.instrumentation.trace_writer import get_trace_writer

        if is_callable:
            original_fn: Callable[..., Any] = data  # type: ignore[assignment]

            @functools.wraps(original_fn)
            def _tracing_callable(*args: Any, **kwargs: Any) -> Any:
                result = original_fn(*args, **kwargs)
                serialized = serialize_wrap_data(result)
                _emit_wrap_event(name, purpose, serialized, description)
                writer = get_trace_writer()
                if writer is not None:
                    writer.write_wrap_event(name, purpose, serialized, description)
                return result

            return _tracing_callable  # type: ignore[return-value]
        else:
            serialized = serialize_wrap_data(data)
            _emit_wrap_event(name, purpose, serialized, description)
            writer = get_trace_writer()
            if writer is not None:
                writer.write_wrap_event(name, purpose, serialized, description)
            return data

    # ── No-op mode ───────────────────────────────────────────────────────────
    return data
