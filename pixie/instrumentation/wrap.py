"""``pixie.wrap`` — data-oriented observation API.

``wrap()`` observes a data value or callable at a named point in the
processing pipeline.  Its behavior depends on the active mode:

- **No-op** (tracing disabled, no eval registry): returns ``data`` unchanged.
- **Tracing** (``PIXIE_TRACING=1``): emits an OTel span event and returns
  ``data`` unchanged (or wraps a callable so the event fires on call).
- **Eval** (eval registry active): injects dependency data for
  ``purpose="input"``, captures output/state for ``purpose="output"``/
  ``purpose="state"``.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, Literal, TypeVar

from opentelemetry import trace

from pixie.config import get_config

from .wrap_registry import get_capture_registry, get_input_registry
from .wrap_serialization import deserialize_wrap_data, serialize_wrap_data

T = TypeVar("T")


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
    """Emit an OTel event for a wrap observation."""
    span = trace.get_current_span()
    if span.is_recording():
        span.add_event(
            "pixie.wrap",
            attributes={
                "wrap.name": name,
                "wrap.purpose": purpose,
                "wrap.data": data_serialized,
                **({"wrap.description": description} if description else {}),
            },
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
    same type it passed in.  The implementation distinguishes the two cases
    internally: for a callable, the actual observation (OTel event / trace
    write) happens when the returned wrapper is called, not at ``wrap()``
    time; and in eval mode the returned wrapper yields the registry value
    instead of invoking the original function.

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
        is callable the return value is also callable with the same
        signature.
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
                # Return a callable that always returns the injected value
                def _injected_callable(*args: Any, **kwargs: Any) -> Any:
                    return deserialized

                return _injected_callable  # type: ignore[return-value]
            return deserialized  # type: ignore[no-any-return]

        elif purpose in ("output", "state"):
            # Capture to capture registry
            capture_reg = get_capture_registry()
            if is_callable:
                original_callable: Callable[..., Any] = data  # type: ignore[assignment]

                @functools.wraps(original_callable)
                def _capturing_callable(*args: Any, **kwargs: Any) -> Any:
                    result = original_callable(*args, **kwargs)
                    if capture_reg is not None:
                        capture_reg[name] = result
                    return result

                return _capturing_callable  # type: ignore[return-value]
            else:
                if capture_reg is not None:
                    capture_reg[name] = data
                return data

        else:
            # purpose == "entry": behave like no-op in eval mode
            return data

    # ── Tracing mode ─────────────────────────────────────────────────────────
    config = get_config()
    if config.tracing_enabled:
        # Lazy import to avoid circular dependency
        from pixie.instrumentation.handlers import get_trace_writer

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
