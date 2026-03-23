"""@observe decorator for automatic function input/output capture."""

from __future__ import annotations

import asyncio
import functools
import inspect
import os
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, TypeVar

import jsonpickle
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Tracer, set_tracer_provider
from pydantic import JsonValue
from typing_extensions import ParamSpec

from .context import ObservationContext, _NoOpObservationContext
from .handler import InstrumentationHandler, _HandlerRegistry
from .instrumentors import _activate_instrumentors
from .processor import LLMSpanProcessor
from .queue import _DeliveryQueue

P = ParamSpec("P")
T = TypeVar("T")


def _serialize(value: Any) -> JsonValue:
    """Serialize a value to a JSON-compatible representation using jsonpickle."""
    return jsonpickle.encode(value, unpicklable=False)  # type: ignore[no-any-return]


def observe(
    name: str | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that wraps a function in a start_observation() block.

    Automatically captures the function's keyword arguments as input and
    the return value as output. Uses jsonpickle for serialization.

    If tracing is not initialized, the function executes normally with no
    overhead beyond the decorator call itself.

    Args:
        name: Optional span name. Defaults to the function's __name__.
    """

    def decorator(fn: Callable[P, T]) -> Callable[P, T]:
        span_name = name or fn.__name__

        if asyncio.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:

                sig = inspect.signature(fn)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                arguments = dict(bound.arguments)
                arguments.pop("self", None)
                arguments.pop("cls", None)
                serialized_input = _serialize(arguments)

                with start_observation(
                    input=serialized_input, name=span_name
                ) as observation:
                    result = await fn(*args, **kwargs)
                    observation.set_output(_serialize(result))
                    return result  # type: ignore[no-any-return]

            return async_wrapper  # type: ignore[return-value]
        else:

            @functools.wraps(fn)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:

                sig = inspect.signature(fn)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                arguments = dict(bound.arguments)
                arguments.pop("self", None)
                arguments.pop("cls", None)
                serialized_input = _serialize(arguments)

                with start_observation(
                    input=serialized_input, name=span_name
                ) as observation:
                    result = fn(*args, **kwargs)
                    observation.set_output(_serialize(result))
                    return result

            return sync_wrapper

    return decorator


@dataclass
class _State:
    registry: _HandlerRegistry | None = None
    delivery_queue: _DeliveryQueue | None = None
    tracer: Tracer | None = None
    tracer_provider: TracerProvider | None = None
    initialized: bool = False


_state = _State()


def _reset_state() -> None:
    """Reset global state. **Test-only** — not part of the public API."""
    if _state.delivery_queue is not None:
        _state.delivery_queue.flush()
    _state.registry = None
    _state.delivery_queue = None
    _state.tracer = None
    _state.tracer_provider = None
    _state.initialized = False


def init(
    *,
    capture_content: bool = True,
    queue_size: int = 1000,
) -> None:
    """Initialize the instrumentation sub-package.

    Sets up the OpenTelemetry ``TracerProvider``, span processor, delivery
    queue, and activates auto-instrumentors.  Truly idempotent — calling
    ``init()`` a second time is a no-op.

    Handler registration is done separately via :func:`add_handler`.
    """
    if _state.initialized:
        return

    if capture_content:
        os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "true"

    registry = _HandlerRegistry()
    delivery_queue = _DeliveryQueue(registry, maxsize=queue_size)
    processor = LLMSpanProcessor(delivery_queue)

    provider = TracerProvider()
    provider.add_span_processor(processor)
    set_tracer_provider(provider)

    _state.registry = registry
    _state.delivery_queue = delivery_queue
    _state.tracer = provider.get_tracer("pixie.instrumentation")
    _state.tracer_provider = provider
    _state.initialized = True

    _activate_instrumentors()


def add_handler(handler: InstrumentationHandler) -> None:
    """Register *handler* to receive span notifications.

    Must be called after :func:`init`.  Multiple handlers can be
    registered; each receives every span.
    """
    if _state.registry is None:
        raise RuntimeError(
            "pixie.instrumentation.init() must be called before add_handler()"
        )
    _state.registry.add(handler)


def remove_handler(handler: InstrumentationHandler) -> None:
    """Unregister a previously registered *handler*.

    Raises ``ValueError`` if *handler* was not registered.
    """
    if _state.registry is None:
        raise RuntimeError(
            "pixie.instrumentation.init() must be called before remove_handler()"
        )
    _state.registry.remove(handler)


@contextmanager
def start_observation(
    *,
    input: JsonValue,
    name: str | None = None,
) -> Generator[ObservationContext, None, None]:
    """Context manager that creates an OTel span and yields a mutable ObservationContext.

    If init() has not been called, yields a no-op context — the wrapped code
    executes normally but no span is captured.
    """
    if _state.tracer is None:
        yield _NoOpObservationContext()
        return

    tracer = _state.tracer
    span_name = name or "observe"
    with tracer.start_as_current_span(span_name) as otel_span:
        ctx = ObservationContext(otel_span=otel_span, input=input)
        try:
            yield ctx
        except Exception as e:
            ctx._error = type(e).__name__
            raise
        finally:
            observe_span = ctx._snapshot()
            if _state.delivery_queue is not None:
                _state.delivery_queue.submit(observe_span)


def flush(timeout_seconds: float = 5.0) -> bool:
    """Flush the delivery queue, blocking until all items are processed."""
    if _state.delivery_queue is not None:
        return _state.delivery_queue.flush(timeout_seconds=timeout_seconds)
    return True
