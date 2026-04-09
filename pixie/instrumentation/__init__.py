"""pixie.instrumentation — tracing and observation API for LLM applications.

Core functions:
    - :func:`enable_llm_tracing` — initialize the tracer provider, span
      processor, delivery queue, and auto-instrumentors (idempotent).
    - :func:`flush` — flush pending spans to handlers.
    - :func:`add_handler` / :func:`remove_handler` — register or unregister
      :class:`InstrumentationHandler` instances to receive span notifications.
    - :func:`wrap` — data-oriented observation API for dependency injection
      and output capture.

Span types:
    - :class:`LLMSpan` — one LLM provider call (chat or embedding).
    - :class:`ObserveSpan` — user-defined instrumented block.

Message types:
    - :class:`SystemMessage`, :class:`UserMessage`, :class:`AssistantMessage`,
      :class:`ToolResultMessage` — LLM conversation messages.
    - :class:`TextContent`, :class:`ImageContent` — multimodal content parts.
    - :class:`ToolCall`, :class:`ToolDefinition` — tool invocation types.

Wrap support:
    - :class:`WrappedData` — Pydantic model for ``wrap()`` observation records.
    - :class:`TraceLogProcessor` — writes wrap events to JSONL trace files.
    - :class:`EvalCaptureLogProcessor` — captures output/state wrap events
      during ``pixie test`` evaluation runs.
"""

from __future__ import annotations

from .llm_tracing import (
    AssistantMessage,
    ImageContent,
    InstrumentationHandler,
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
    add_handler,
    enable_llm_tracing,
    flush,
    remove_handler,
)
from .models import ENTRY_KWARGS_KEY
from .wrap import (
    EvalCaptureLogProcessor,
    TraceLogProcessor,
    WrapNameCollisionError,
    WrappedData,
    WrapRegistryMissError,
    WrapTypeMismatchError,
    clear_eval_input,
    clear_eval_output,
    ensure_eval_capture_registered,
    filter_by_purpose,
    get_eval_input,
    get_eval_output,
    init_eval_output,
    set_eval_input,
    wrap,
)

__all__ = [
    "AssistantMessage",
    "ENTRY_KWARGS_KEY",
    "EvalCaptureLogProcessor",
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
    "TraceLogProcessor",
    "UserMessage",
    "WrapNameCollisionError",
    "WrapRegistryMissError",
    "WrapTypeMismatchError",
    "WrappedData",
    "add_handler",
    "clear_eval_input",
    "clear_eval_output",
    "ensure_eval_capture_registered",
    "flush",
    "filter_by_purpose",
    "get_eval_input",
    "get_eval_output",
    "enable_llm_tracing",
    "init_eval_output",
    "set_eval_input",
    "remove_handler",
    "wrap",
]
