"""pixie.instrumentation — public API: init(), log(), flush()."""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Tracer, set_tracer_provider

from .context import _SpanContext
from .handler import InstrumentationHandler
from .instrumentors import _activate_instrumentors
from .processor import LLMSpanProcessor
from .queue import _DeliveryQueue
from .spans import (
    AssistantMessage,
    ImageContent,
    LLMSpan,
    Message,
    MessageContent,
    ObserveSpan,
    SystemMessage,
    TextContent,
    ToolCall,
    ToolDefinition,
    ToolResultMessage,
    UserMessage,
)


@dataclass
class _State:
    delivery_queue: _DeliveryQueue | None = None
    tracer: Tracer | None = None
    tracer_provider: TracerProvider | None = None
    initialized: bool = False


_state = _State()


def init(
    handler: InstrumentationHandler,
    *,
    capture_content: bool = False,
    queue_size: int = 1000,
) -> None:
    """Initialize the instrumentation sub-package. Idempotent."""
    if capture_content:
        os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "true"

    # Flush existing queue on re-init
    if _state.delivery_queue is not None:
        _state.delivery_queue.flush()

    delivery_queue = _DeliveryQueue(handler, maxsize=queue_size)
    processor = LLMSpanProcessor(delivery_queue)

    provider = TracerProvider()
    provider.add_span_processor(processor)
    set_tracer_provider(provider)

    _state.delivery_queue = delivery_queue
    _state.tracer = provider.get_tracer("pixie.instrumentation")
    _state.tracer_provider = provider
    _state.initialized = True

    _activate_instrumentors()


@contextmanager
def log(
    input: Any = None, *, name: str | None = None  # noqa: A002
) -> Generator[_SpanContext, None, None]:
    """Context manager that creates an OTel span and yields a mutable _SpanContext.

    On exit, snapshots the context into a frozen ObserveSpan delivered to the handler.
    """
    if _state.tracer is None:
        raise RuntimeError("pixie.instrumentation.init() must be called before log()")
    tracer = _state.tracer
    span_name = name or "observe"
    with tracer.start_as_current_span(span_name) as otel_span:
        ctx = _SpanContext(otel_span=otel_span, input=input)
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


__all__ = [
    "AssistantMessage",
    "ImageContent",
    "InstrumentationHandler",
    "LLMSpan",
    "Message",
    "MessageContent",
    "ObserveSpan",
    "SystemMessage",
    "TextContent",
    "ToolCall",
    "ToolDefinition",
    "ToolResultMessage",
    "UserMessage",
    "flush",
    "init",
    "log",
]
