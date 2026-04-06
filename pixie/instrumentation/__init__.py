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

from .handler import InstrumentationHandler
from .observation import (
    add_handler,
    flush,
    init,
    remove_handler,
)
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
from .wrap import WrapRegistryMissError, WrapTypeMismatchError, wrap
from .wrap_log import (
    WrapLogEntry,
    WrappedData,
    filter_by_purpose,
    load_wrap_log_entries,
    parse_wrapped_data_list,
)
from .wrap_registry import (
    clear_capture_registry,
    clear_input_registry,
    get_capture_registry,
    get_input_registry,
    get_output_capture_registry,
    get_state_capture_registry,
    init_capture_registry,
    set_input_registry,
)

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
    "WrapRegistryMissError",
    "WrapTypeMismatchError",
    "WrapLogEntry",
    "WrappedData",
    "add_handler",
    "clear_capture_registry",
    "clear_input_registry",
    "flush",
    "filter_by_purpose",
    "get_capture_registry",
    "get_input_registry",
    "get_output_capture_registry",
    "get_state_capture_registry",
    "init",
    "init_capture_registry",
    "load_wrap_log_entries",
    "parse_wrapped_data_list",
    "set_input_registry",
    "remove_handler",
    "wrap",
]
