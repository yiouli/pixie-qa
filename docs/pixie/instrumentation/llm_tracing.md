Module pixie.instrumentation.llm_tracing
========================================
pixie.instrumentation.llm_tracing — LLM call tracing and span processing.

Combines all LLM tracing functionality:
- Data model types for instrumentation spans (LLMSpan, ObserveSpan, messages)
- InstrumentationHandler base class and handler registry
- DeliveryQueue background worker thread
- LLMSpanProcessor (OTel SpanProcessor)
- Auto-discovery and activation of OpenInference instrumentors
- Instrumentation initialization and handler management

Functions
---------

`def add_handler(handler: InstrumentationHandler) ‑> None`
:   Register *handler* to receive span notifications.
    
    Must be called after :func:`enable_llm_tracing`.  Multiple handlers can
    be registered; each receives every span.

`def enable_llm_tracing(*, capture_content: bool = True, queue_size: int = 1000) ‑> None`
:   Initialize the LLM tracing sub-system.
    
    Sets up the OpenTelemetry ``TracerProvider``, span processor, delivery
    queue, and activates auto-instrumentors for known LLM providers.
    Truly idempotent — calling ``enable_llm_tracing()`` a second time is
    a no-op.
    
    Handler registration is done separately via :func:`add_handler`.

`def flush(timeout_seconds: float = 5.0) ‑> bool`
:   Flush the delivery queue, blocking until all items are processed.

`def remove_handler(handler: InstrumentationHandler) ‑> None`
:   Unregister a previously registered *handler*.
    
    Raises ``ValueError`` if *handler* was not registered.

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

`LLMSpanProcessor(delivery_queue: _DeliveryQueue)`
:   OTel SpanProcessor that converts OpenInference LLM spans to typed LLMSpan objects.

    ### Ancestors (in MRO)

    * opentelemetry.sdk.trace.SpanProcessor

    ### Methods

    `def force_flush(self, timeout_millis: int = 30000) ‑> bool`
    :   Flush the delivery queue.

    `def on_end(self, span: ReadableSpan) ‑> None`
    :   Convert completed OpenInference LLM spans to LLMSpan and submit.

    `def on_shutdown(self) ‑> None`
    :   No-op.

    `def on_start(self, span: Any, parent_context: Any = None) ‑> None`
    :   No-op — we only process completed spans.

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