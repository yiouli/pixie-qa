"""pixie.instrumentation — public API for tracing and observing LLM applications.

Core functions:
    - ``init()`` — initialize the tracer provider, span processor, and auto-instrumentors.
    - ``flush()`` — flush pending spans to handlers.
    - ``add_handler()`` / ``remove_handler()`` — register span handlers.
    - ``wrap()`` — data-oriented observation API for dependency injection and output capture.

Configuration
-------------

| Variable | Default | Description |
| --- | --- | --- |
| ``PIXIE_ROOT`` | ``pixie_qa`` | Root directory for all pixie-generated artefacts |
| ``PIXIE_DATASET_DIR`` | ``{PIXIE_ROOT}/datasets`` | Directory for dataset JSON files |
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
from .wrap import (
    EvalCaptureLogProcessor,
    TraceLogProcessor,
    WrapLogEntry,
    WrapRegistryMissError,
    WrapTypeMismatchError,
    WrappedData,
    clear_eval_input,
    clear_eval_output,
    ensure_eval_capture_registered,
    filter_by_purpose,
    get_eval_input,
    get_eval_output,
    init_eval_output,
    load_wrap_log_entries,
    parse_wrapped_data_list,
    set_eval_input,
    wrap,
)

__all__ = [
    "AssistantMessage",
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
    "WrapRegistryMissError",
    "WrapTypeMismatchError",
    "WrapLogEntry",
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
    "load_wrap_log_entries",
    "parse_wrapped_data_list",
    "set_eval_input",
    "remove_handler",
    "wrap",
]
