"""pixie.instrumentation — public API for tracing and observing LLM applications.

Core functions:
    - ``init()`` — initialize the tracer provider.
    - ``observe`` — decorator for automatic function input/output capture.
    - ``start_observation()`` — context-manager for manual observation blocks.
    - ``flush()`` — flush pending spans to handlers.
    - ``add_handler()`` / ``remove_handler()`` — register span handlers.
    - ``enable_storage()`` — enable SQLite-backed span persistence.

Configuration
-------------

| Variable | Default | Description |
| --- | --- | --- |
| ``PIXIE_ROOT`` | ``pixie_qa`` | Root directory for all pixie-generated artefacts |
| ``PIXIE_DB_PATH`` | ``{PIXIE_ROOT}/pixie.db`` | SQLite database for captured spans |
| ``PIXIE_DATASET_DIR`` | ``{PIXIE_ROOT}/datasets`` | Directory for dataset JSON files |

CLI Commands
------------

| Command | Description |
| --- | --- |
| ``pixie init [root]`` | Scaffold the ``pixie_qa`` working directory |
| ``pixie trace list [--limit N] [--errors]`` | List recent traces |
| ``pixie trace show <trace_id> [-v] [--json]`` | Show span tree for a trace |
| ``pixie trace last [--json]`` | Show the most recent trace (verbose) |
| ``pixie trace verify`` | Verify the most recent trace for common issues |
| ``pixie dag validate <json>`` | Validate a DAG JSON file |
| ``pixie dag check-trace <json>`` | Check the last trace against a DAG |
"""

from __future__ import annotations

from .handler import InstrumentationHandler
from .observation import (
    add_handler,
    flush,
    init,
    observe,
    remove_handler,
    start_observation,
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
from .wrap_registry import (
    clear_capture_registry,
    clear_input_registry,
    get_capture_registry,
    get_input_registry,
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
    "add_handler",
    "clear_capture_registry",
    "clear_input_registry",
    "flush",
    "get_capture_registry",
    "get_input_registry",
    "init",
    "init_capture_registry",
    "observe",
    "set_input_registry",
    "start_observation",
    "remove_handler",
    "wrap",
]
