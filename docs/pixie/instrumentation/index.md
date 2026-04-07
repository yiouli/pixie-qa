Module pixie.instrumentation
============================
pixie.instrumentation — tracing and observation API for LLM applications.

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

Sub-modules
-----------
* pixie.instrumentation.llm_tracing

Functions
---------

`def add_handler(handler: InstrumentationHandler) ‑> None`
:   Register *handler* to receive span notifications.
    
    Must be called after :func:`enable_llm_tracing`.  Multiple handlers can
    be registered; each receives every span.

`def clear_eval_input() ‑> None`
:   Clear the eval input registry.

`def clear_eval_output() ‑> None`
:   Clear the eval output list.

`def enable_llm_tracing(*, capture_content: bool = True, queue_size: int = 1000) ‑> None`
:   Initialize the LLM tracing sub-system.
    
    Sets up the OpenTelemetry ``TracerProvider``, span processor, delivery
    queue, and activates auto-instrumentors for known LLM providers.
    Truly idempotent — calling ``enable_llm_tracing()`` a second time is
    a no-op.
    
    Handler registration is done separately via :func:`add_handler`.

`def ensure_eval_capture_registered() ‑> None`
:   Register a single :class:`EvalCaptureLogProcessor` on the wrap logger.
    
    Safe to call multiple times — only the first call has an effect.

`def filter_by_purpose(entries: list[WrappedData], purposes: set[str]) ‑> list[pixie.instrumentation.wrap.WrappedData]`
:   Filter wrap log entries by purpose.
    
    Args:
        entries: List of wrap data entries.
        purposes: Set of purpose values to include.
    
    Returns:
        Filtered list.

`def flush(timeout_seconds: float = 5.0) ‑> bool`
:   Flush the delivery queue, blocking until all items are processed.

`def get_eval_input() ‑> collections.abc.Mapping[str, JsonValue] | None`
:   Get the eval input registry, or ``None`` if not in eval mode.

`def get_eval_output() ‑> list[dict[str, typing.Any]] | None`
:   Get the eval output list, or ``None`` if not initialised.

`def init_eval_output() ‑> list[dict[str, typing.Any]]`
:   Initialise and return a fresh eval output list.

`def remove_handler(handler: InstrumentationHandler) ‑> None`
:   Unregister a previously registered *handler*.
    
    Raises ``ValueError`` if *handler* was not registered.

`def set_eval_input(registry: Mapping[str, JsonValue]) ‑> None`
:   Set the eval input registry for the current context.

`def wrap(data: T, *, purpose: Purpose, name: str, description: str | None = None) ‑> ~T`
:   Observe *data* at a named wrap point with a specified purpose.

Classes
-------

`AssistantMessage(content: tuple[MessageContent, ...], tool_calls: tuple[ToolCall, ...], finish_reason: str | None = None, role: "Literal['assistant']" = 'assistant')`
:   Assistant response message with optional tool calls.

    ### Instance variables

    `content: tuple[pixie.instrumentation.llm_tracing.TextContent | pixie.instrumentation.llm_tracing.ImageContent, ...]`
    :

    `finish_reason: str | None`
    :

    `role: Literal['assistant']`
    :

    `tool_calls: tuple[pixie.instrumentation.llm_tracing.ToolCall, ...]`
    :

`EvalCaptureLogProcessor()`
:   Append wrap event bodies to the ``eval_output`` context variable.
    
    Only events with ``purpose="output"`` or ``purpose="state"`` are
    captured.  The processor is a no-op when ``eval_output`` has not been
    initialised (i.e. outside of an eval run).

    ### Ancestors (in MRO)

    * opentelemetry.sdk._logs._internal.LogRecordProcessor
    * abc.ABC

    ### Methods

    `def force_flush(self, timeout_millis: int = 30000) ‑> bool`
    :   Export all the received logs to the configured Exporter that have not yet
        been exported.
        
        Args:
            timeout_millis: The maximum amount of time to wait for logs to be
                exported.
        
        Returns:
            False if the timeout is exceeded, True otherwise.

    `def on_emit(self, log_record: ReadWriteLogRecord) ‑> None`
    :   Emits the ``ReadWriteLogRecord``.
        
        Implementers should handle any exceptions raised during log processing
        to prevent application crashes. See the class docstring for details
        on error handling expectations.

    `def shutdown(self) ‑> None`
    :   Called when a :class:`opentelemetry.sdk._logs.Logger` is shutdown

`ImageContent(url: str, detail: str | None = None, type: "Literal['image']" = 'image')`
:   Image content part (URL or data URI).

    ### Instance variables

    `detail: str | None`
    :

    `type: Literal['image']`
    :

    `url: str`
    :

`InstrumentationHandler()`
:   Base class for instrumentation handlers.
    
    Both methods are optional async overrides — a handler only implementing
    on_llm is valid, and vice versa.  Implementations may be long-running
    (e.g. calling external APIs) since each handler coroutine runs
    concurrently with other registered handlers.

    ### Descendants

    * pixie.cli.trace_command.LLMTraceLogger
    * pixie.instrumentation.llm_tracing._HandlerRegistry

    ### Methods

    `async def on_llm(self, span: LLMSpan) ‑> None`
    :   Called when an LLM provider call completes.
        
        Default: no-op. Override to capture LLM call data for root-cause analysis.
        Exceptions are caught and suppressed.

    `async def on_observe(self, span: ObserveSpan) ‑> None`
    :   Called when a start_observation() block completes.
        
        Default: no-op. Override to capture eval-relevant data.
        Exceptions are caught and suppressed.

`LLMSpan(span_id: str, trace_id: str, parent_span_id: str | None, started_at: datetime, ended_at: datetime, duration_ms: float, operation: str, provider: str, request_model: str, response_model: str | None, input_tokens: int, output_tokens: int, cache_read_tokens: int, cache_creation_tokens: int, request_temperature: float | None, request_max_tokens: int | None, request_top_p: float | None, finish_reasons: tuple[str, ...], response_id: str | None, output_type: str | None, error_type: str | None, input_messages: tuple[Message, ...], output_messages: tuple[AssistantMessage, ...], tool_definitions: tuple[ToolDefinition, ...])`
:   One LLM provider call, produced by LLMSpanProcessor from OpenInference attrs.

    ### Instance variables

    `cache_creation_tokens: int`
    :

    `cache_read_tokens: int`
    :

    `duration_ms: float`
    :

    `ended_at: datetime.datetime`
    :

    `error_type: str | None`
    :

    `finish_reasons: tuple[str, ...]`
    :

    `input_messages: tuple[pixie.instrumentation.llm_tracing.SystemMessage | pixie.instrumentation.llm_tracing.UserMessage | pixie.instrumentation.llm_tracing.AssistantMessage | pixie.instrumentation.llm_tracing.ToolResultMessage, ...]`
    :

    `input_tokens: int`
    :

    `operation: str`
    :

    `output_messages: tuple[pixie.instrumentation.llm_tracing.AssistantMessage, ...]`
    :

    `output_tokens: int`
    :

    `output_type: str | None`
    :

    `parent_span_id: str | None`
    :

    `provider: str`
    :

    `request_max_tokens: int | None`
    :

    `request_model: str`
    :

    `request_temperature: float | None`
    :

    `request_top_p: float | None`
    :

    `response_id: str | None`
    :

    `response_model: str | None`
    :

    `span_id: str`
    :

    `started_at: datetime.datetime`
    :

    `tool_definitions: tuple[pixie.instrumentation.llm_tracing.ToolDefinition, ...]`
    :

    `trace_id: str`
    :

`ObserveSpan(span_id: str, trace_id: str, parent_span_id: str | None, started_at: datetime, ended_at: datetime, duration_ms: float, name: str | None, input: Any, output: Any, metadata: dict[str, Any], error: str | None)`
:   A user-defined instrumented block, produced when a log() block exits.

    ### Instance variables

    `duration_ms: float`
    :

    `ended_at: datetime.datetime`
    :

    `error: str | None`
    :

    `input: Any`
    :

    `metadata: dict[str, typing.Any]`
    :

    `name: str | None`
    :

    `output: Any`
    :

    `parent_span_id: str | None`
    :

    `span_id: str`
    :

    `started_at: datetime.datetime`
    :

    `trace_id: str`
    :

`SystemMessage(content: str, role: "Literal['system']" = 'system')`
:   System prompt message.

    ### Instance variables

    `content: str`
    :

    `role: Literal['system']`
    :

`TextContent(text: str, type: "Literal['text']" = 'text')`
:   Plain text content part.

    ### Instance variables

    `text: str`
    :

    `type: Literal['text']`
    :

`ToolCall(name: str, arguments: dict[str, Any], id: str | None = None)`
:   Tool invocation requested by the model.

    ### Instance variables

    `arguments: dict[str, typing.Any]`
    :

    `id: str | None`
    :

    `name: str`
    :

`ToolDefinition(name: str, description: str | None = None, parameters: dict[str, Any] | None = None)`
:   Tool made available to the model in the request.

    ### Instance variables

    `description: str | None`
    :

    `name: str`
    :

    `parameters: dict[str, typing.Any] | None`
    :

`ToolResultMessage(content: str, tool_call_id: str | None = None, tool_name: str | None = None, role: "Literal['tool']" = 'tool')`
:   Tool execution result message.

    ### Instance variables

    `content: str`
    :

    `role: Literal['tool']`
    :

    `tool_call_id: str | None`
    :

    `tool_name: str | None`
    :

`TraceLogProcessor(output_path: str)`
:   Write wrap event bodies as JSON lines to a file.
    
    Args:
        output_path: Path to the JSONL trace file.  Parent directories
            are created if missing; the file is truncated on init.

    ### Ancestors (in MRO)

    * opentelemetry.sdk._logs._internal.LogRecordProcessor
    * abc.ABC

    ### Methods

    `def force_flush(self, timeout_millis: int = 30000) ‑> bool`
    :   Export all the received logs to the configured Exporter that have not yet
        been exported.
        
        Args:
            timeout_millis: The maximum amount of time to wait for logs to be
                exported.
        
        Returns:
            False if the timeout is exceeded, True otherwise.

    `def on_emit(self, log_record: ReadWriteLogRecord) ‑> None`
    :   Emits the ``ReadWriteLogRecord``.
        
        Implementers should handle any exceptions raised during log processing
        to prevent application crashes. See the class docstring for details
        on error handling expectations.

    `def shutdown(self) ‑> None`
    :   Called when a :class:`opentelemetry.sdk._logs.Logger` is shutdown

    `def write_line(self, record: dict[str, Any]) ‑> None`
    :   Write an arbitrary JSON record (e.g. kwargs, llm_span).

`UserMessage(content: tuple[MessageContent, ...], role: "Literal['user']" = 'user')`
:   User message with multimodal content parts.

    ### Static methods

    `def from_text(text: str) ‑> pixie.instrumentation.llm_tracing.UserMessage`
    :   Create a UserMessage with a single TextContent part.

    ### Instance variables

    `content: tuple[pixie.instrumentation.llm_tracing.TextContent | pixie.instrumentation.llm_tracing.ImageContent, ...]`
    :

    `role: Literal['user']`
    :

`WrapRegistryMissError(name: str)`
:   Raised when a wrap(purpose="input") name is not found in the eval registry.

    ### Ancestors (in MRO)

    * builtins.KeyError
    * builtins.LookupError
    * builtins.Exception
    * builtins.BaseException

`WrapTypeMismatchError(name: str, expected_type: type, actual_type: type)`
:   Raised when deserialized registry value doesn't match expected type.

    ### Ancestors (in MRO)

    * builtins.TypeError
    * builtins.Exception
    * builtins.BaseException

`WrappedData(**data: Any)`
:   A single ``wrap()`` observation record.
    
    Used in three contexts:
    
    1. **Trace files** — written to JSONL by the trace writer.
    2. **Dataset ``eval_input``** — each dataset item stores its input
       as ``list[WrappedData]`` (JSON-serialized).
    3. **In-memory emission** — created by ``wrap()`` before dispatching.
    
    Attributes:
        type: Always ``"wrap"`` for wrap events.
        name: The wrap point name (matches ``wrap(name=...)``).
        purpose: One of `"input"``, ``"output"``, ``"state"``.
        data: The observed data value (stored as JSON-compatible value).
        description: Optional human-readable description.
        trace_id: OTel trace ID (if available).
        span_id: OTel span ID (if available).
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel

    ### Class variables

    `data: JsonValue`
    :

    `description: str | None`
    :

    `model_config`
    :

    `name: str`
    :

    `purpose: Literal['input', 'output', 'state']`
    :

    `span_id: str | None`
    :

    `trace_id: str | None`
    :

    `type: str`
    :