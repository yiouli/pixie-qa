"""Instrumentation initialization and handler management."""

from __future__ import annotations

import os
from dataclasses import dataclass

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Tracer, set_tracer_provider

from .handler import InstrumentationHandler, _HandlerRegistry
from .instrumentors import _activate_instrumentors
from .processor import LLMSpanProcessor
from .queue import _DeliveryQueue


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

    When ``PIXIE_TRACING=1`` and ``PIXIE_TRACE_OUTPUT`` is set, a
    :class:`~pixie.instrumentation.trace_writer.TraceFileWriter` is also
    created for ``wrap()`` and ``LLMSpanProcessor`` to use.

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

    # Set up trace file writer when tracing is enabled
    from pixie.config import get_config

    config = get_config()
    if config.tracing_enabled and config.trace_output:
        from pixie.instrumentation.trace_writer import TraceFileWriter, set_trace_writer

        set_trace_writer(TraceFileWriter(config.trace_output))


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


def flush(timeout_seconds: float = 5.0) -> bool:
    """Flush the delivery queue, blocking until all items are processed."""
    if _state.delivery_queue is not None:
        return _state.delivery_queue.flush(timeout_seconds=timeout_seconds)
    return True
