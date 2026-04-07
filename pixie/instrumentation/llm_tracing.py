"""pixie.instrumentation.llm_tracing — LLM call tracing and span processing.

Combines all LLM tracing functionality:
- Data model types for instrumentation spans (LLMSpan, ObserveSpan, messages)
- InstrumentationHandler base class and handler registry
- DeliveryQueue background worker thread
- LLMSpanProcessor (OTel SpanProcessor)
- Auto-discovery and activation of OpenInference instrumentors
- Instrumentation initialization and handler management
"""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
import os
import queue
import threading
from concurrent.futures import Future
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal  # noqa: UP035

from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor, TracerProvider
from opentelemetry.trace import StatusCode, Tracer, set_tracer_provider

logger = logging.getLogger("pixie.instrumentation")

# ── Message content types ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class TextContent:
    """Plain text content part."""

    text: str
    type: Literal["text"] = "text"


@dataclass(frozen=True)
class ImageContent:
    """Image content part (URL or data URI)."""

    url: str  # https:// or data: URI
    detail: str | None = None  # "low" | "high" | "auto" | None
    type: Literal["image"] = "image"


MessageContent = TextContent | ImageContent


# ── Tool types ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ToolCall:
    """Tool invocation requested by the model."""

    name: str
    arguments: dict[str, Any]  # always deserialized, never a raw JSON string
    id: str | None = None


@dataclass(frozen=True)
class ToolDefinition:
    """Tool made available to the model in the request."""

    name: str
    description: str | None = None
    parameters: dict[str, Any] | None = None  # JSON Schema object


# ── Message types ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SystemMessage:
    """System prompt message."""

    content: str
    role: Literal["system"] = "system"


@dataclass(frozen=True)
class UserMessage:
    """User message with multimodal content parts."""

    content: tuple[MessageContent, ...]
    role: Literal["user"] = "user"

    @classmethod
    def from_text(cls, text: str) -> UserMessage:
        """Create a UserMessage with a single TextContent part."""
        return cls(content=(TextContent(text=text),))


@dataclass(frozen=True)
class AssistantMessage:
    """Assistant response message with optional tool calls."""

    content: tuple[MessageContent, ...]
    tool_calls: tuple[ToolCall, ...]
    finish_reason: str | None = None
    role: Literal["assistant"] = "assistant"


@dataclass(frozen=True)
class ToolResultMessage:
    """Tool execution result message."""

    content: str
    tool_call_id: str | None = None
    tool_name: str | None = None
    role: Literal["tool"] = "tool"


Message = SystemMessage | UserMessage | AssistantMessage | ToolResultMessage


# ── Span types ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LLMSpan:
    """One LLM provider call, produced by LLMSpanProcessor from OpenInference attrs."""

    # ── Identity
    span_id: str  # hex, 16 chars
    trace_id: str  # hex, 32 chars
    parent_span_id: str | None  # links to ObserveSpan.span_id when nested

    # ── Timing
    started_at: datetime
    ended_at: datetime
    duration_ms: float

    # ── Provider / model
    operation: str  # "chat" | "embedding"
    provider: str  # "openai" | "anthropic" | "google" | ...
    request_model: str
    response_model: str | None

    # ── Token usage
    input_tokens: int  # default 0
    output_tokens: int  # default 0
    cache_read_tokens: int  # default 0
    cache_creation_tokens: int  # default 0

    # ── Request parameters
    request_temperature: float | None
    request_max_tokens: int | None
    request_top_p: float | None

    # ── Response metadata
    finish_reasons: tuple[str, ...]  # default ()
    response_id: str | None
    output_type: str | None  # "json" | "text" | None
    error_type: str | None

    # ── Content (populated when capture_content=True)
    input_messages: tuple[Message, ...]  # default ()
    output_messages: tuple[AssistantMessage, ...]  # default ()
    tool_definitions: tuple[ToolDefinition, ...]  # always populated when available


@dataclass(frozen=True)
class ObserveSpan:
    """A user-defined instrumented block, produced when a log() block exits."""

    # ── Identity
    span_id: str  # hex, 16 chars
    trace_id: str  # hex, 32 chars
    parent_span_id: str | None

    # ── Timing
    started_at: datetime
    ended_at: datetime
    duration_ms: float

    # ── User-defined fields
    name: str | None  # optional label for the block
    input: Any  # value passed to log(input=...)
    output: Any  # value set via span.set_output(...)
    metadata: dict[str, Any]  # accumulated via span.set_metadata(k, v)
    error: str | None  # exception type if block raised, else None


# ── InstrumentationHandler ────────────────────────────────────────────────────


class InstrumentationHandler:
    """Base class for instrumentation handlers.

    Both methods are optional async overrides — a handler only implementing
    on_llm is valid, and vice versa.  Implementations may be long-running
    (e.g. calling external APIs) since each handler coroutine runs
    concurrently with other registered handlers.
    """

    async def on_llm(self, span: LLMSpan) -> None:
        """Called when an LLM provider call completes.

        Default: no-op. Override to capture LLM call data for root-cause analysis.
        Exceptions are caught and suppressed.
        """

    async def on_observe(self, span: ObserveSpan) -> None:
        """Called when a start_observation() block completes.

        Default: no-op. Override to capture eval-relevant data.
        Exceptions are caught and suppressed.
        """


class _HandlerRegistry(InstrumentationHandler):
    """Fan-out handler that dispatches to multiple registered handlers.

    Thread-safe: handlers can be added/removed from any thread.
    Each handler coroutine runs concurrently via ``asyncio.gather``;
    per-handler exceptions are isolated so one failing handler does not
    prevent delivery to the remaining handlers.
    """

    def __init__(self) -> None:
        self._handlers: list[InstrumentationHandler] = []
        self._lock = threading.Lock()

    def add(self, handler: InstrumentationHandler) -> None:
        """Register *handler* to receive span notifications."""
        with self._lock:
            self._handlers.append(handler)

    def remove(self, handler: InstrumentationHandler) -> None:
        """Unregister *handler*. Raises ``ValueError`` if not found."""
        with self._lock:
            self._handlers.remove(handler)

    async def on_llm(self, span: LLMSpan) -> None:
        """Dispatch to all registered handlers concurrently, isolating exceptions."""
        with self._lock:
            snapshot = list(self._handlers)
        await asyncio.gather(
            *(h.on_llm(span) for h in snapshot), return_exceptions=True
        )

    async def on_observe(self, span: ObserveSpan) -> None:
        """Dispatch to all registered handlers concurrently, isolating exceptions."""
        with self._lock:
            snapshot = list(self._handlers)
        await asyncio.gather(
            *(h.on_observe(span) for h in snapshot), return_exceptions=True
        )


# ── DeliveryQueue ─────────────────────────────────────────────────────────────


class _DeliveryQueue:
    """Single queue for both LLMSpan and ObserveSpan.

    A dedicated asyncio event loop runs on a background daemon thread.  The
    queue-worker thread picks up each span and schedules an async dispatch
    coroutine on that loop (fire and forget from the worker's perspective).
    ``queue.task_done()`` is called via a ``Future`` done-callback once the
    coroutine finishes, so ``flush()`` (which calls ``queue.join()``) correctly
    waits for all in-flight async processing to complete.
    """

    def __init__(self, handler: InstrumentationHandler, maxsize: int = 1000) -> None:
        self._handler = handler
        self._queue: queue.Queue[LLMSpan | ObserveSpan] = queue.Queue(maxsize=maxsize)
        self._dropped_count = 0

        # Dedicated event loop running on its own daemon thread.
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._loop.run_forever,
            daemon=True,
            name="pixie-asyncio-loop",
        )
        self._loop_thread.start()

        # Queue-consumer thread: picks items and schedules async tasks.
        self._thread = threading.Thread(
            target=self._worker, daemon=True, name="pixie-delivery-worker"
        )
        self._thread.start()

    def submit(self, item: LLMSpan | ObserveSpan) -> None:
        """Submit a span for delivery. Drops silently on full queue."""
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            self._dropped_count += 1

    def flush(self, timeout_seconds: float = 5.0) -> bool:
        """Block until all queued items and their async handlers are done."""
        try:
            self._queue.join()
            return True
        except Exception:
            return False

    def _worker(self) -> None:
        """Queue-consumer: fire-and-forget async dispatch for each span."""
        while True:
            item = self._queue.get()
            try:
                future: Future[None] = asyncio.run_coroutine_threadsafe(
                    self._dispatch(item), self._loop
                )
                # task_done() is deferred until the coroutine finishes so
                # that flush() / queue.join() waits for async handlers too.
                future.add_done_callback(lambda _f: self._queue.task_done())
            except Exception:
                # Scheduling failed — mark done immediately to avoid deadlock.
                self._queue.task_done()

    async def _dispatch(self, item: LLMSpan | ObserveSpan) -> None:
        """Async dispatch: route span to the appropriate handler method."""
        try:
            if isinstance(item, LLMSpan):
                await self._handler.on_llm(item)
            elif isinstance(item, ObserveSpan):
                await self._handler.on_observe(item)
        except Exception:
            pass  # Handler exceptions are silently swallowed

    @property
    def dropped_count(self) -> int:
        """Number of spans dropped due to full queue."""
        return self._dropped_count


# ── LLMSpanProcessor ─────────────────────────────────────────────────────────


class LLMSpanProcessor(SpanProcessor):
    """OTel SpanProcessor that converts OpenInference LLM spans to typed LLMSpan objects."""

    def __init__(self, delivery_queue: _DeliveryQueue) -> None:
        self._delivery_queue = delivery_queue

    def on_start(self, span: Any, parent_context: Any = None) -> None:
        """No-op — we only process completed spans."""

    def on_end(self, span: ReadableSpan) -> None:
        """Convert completed OpenInference LLM spans to LLMSpan and submit."""
        try:
            attrs = dict(span.attributes) if span.attributes else {}

            # Only process LLM spans
            span_kind = attrs.get("openinference.span.kind")
            if span_kind not in ("LLM", "EMBEDDING"):
                return

            llm_span = self._build_llm_span(span, attrs, str(span_kind))
            self._delivery_queue.submit(llm_span)

        except Exception:
            pass  # Never raise from on_end

    def on_shutdown(self) -> None:
        """No-op."""

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Flush the delivery queue."""
        return self._delivery_queue.flush(timeout_seconds=timeout_millis / 1000)

    def _build_llm_span(
        self,
        span: ReadableSpan,
        attrs: dict[str, Any],
        span_kind: str,
    ) -> LLMSpan:
        """Build a typed LLMSpan from raw OTel span and attributes."""
        # ── Identity / timing
        ctx = span.context
        if ctx is None:
            raise ValueError("No span context")
        span_id = format(ctx.span_id, "016x")
        trace_id = format(ctx.trace_id, "032x")
        parent_span_id = format(span.parent.span_id, "016x") if span.parent else None

        start_ns = span.start_time or 0
        end_ns = span.end_time or 0
        started_at = datetime.fromtimestamp(start_ns / 1e9, tz=timezone.utc)
        ended_at = datetime.fromtimestamp(end_ns / 1e9, tz=timezone.utc)
        duration_ms = (end_ns - start_ns) / 1e6

        # ── Provider / model
        request_model = str(attrs.get("llm.model_name") or attrs.get("gen_ai.request.model", ""))
        response_model_raw = attrs.get("gen_ai.response.model")
        response_model = str(response_model_raw) if response_model_raw is not None else None
        provider = str(attrs.get("gen_ai.system", "")) or _infer_provider(request_model)
        operation = "embedding" if span_kind == "EMBEDDING" else "chat"

        # ── Token usage
        input_tokens = int(attrs.get("llm.token_count.prompt", 0))
        output_tokens = int(attrs.get("llm.token_count.completion", 0))
        cache_read_tokens = int(attrs.get("llm.token_count.cache_read", 0))
        cache_creation_tokens = int(attrs.get("llm.token_count.cache_creation", 0))

        # ── Request parameters
        params = _parse_json(str(attrs.get("llm.invocation_parameters", "{}")))
        request_temperature = _to_float_or_none(params.get("temperature"))
        request_max_tokens = _to_int_or_none(
            params.get("max_tokens") or params.get("max_completion_tokens")
        )
        request_top_p = _to_float_or_none(params.get("top_p"))

        # ── Response / error
        response_id_raw = attrs.get("llm.response_id") or attrs.get("gen_ai.response.id")
        response_id = str(response_id_raw) if response_id_raw is not None else None
        output_type_raw = attrs.get("gen_ai.output.type")
        output_type = str(output_type_raw) if output_type_raw is not None else None
        error_type_raw = attrs.get("error.type")
        if error_type_raw is not None:
            error_type: str | None = str(error_type_raw)
        elif span.status and span.status.status_code == StatusCode.ERROR:
            error_type = "error"
        else:
            error_type = None

        # ── Messages
        input_messages = _parse_input_messages(attrs)
        output_messages = _parse_output_messages(attrs)
        finish_reasons = tuple(msg.finish_reason for msg in output_messages if msg.finish_reason)

        # ── Tool definitions
        tool_definitions = _parse_tool_definitions(attrs)

        return LLMSpan(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
            operation=operation,
            provider=provider,
            request_model=request_model,
            response_model=response_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_creation_tokens=cache_creation_tokens,
            request_temperature=request_temperature,
            request_max_tokens=request_max_tokens,
            request_top_p=request_top_p,
            finish_reasons=finish_reasons,
            response_id=response_id,
            output_type=output_type,
            error_type=error_type,
            input_messages=tuple(input_messages),
            output_messages=tuple(output_messages),
            tool_definitions=tuple(tool_definitions),
        )


# ── Processor helper functions ────────────────────────────────────────────────


def _infer_provider(model_name: str) -> str:
    """Infer the LLM provider from the model name."""
    lower = model_name.lower()
    if "gpt" in lower or "o1" in lower or "o3" in lower:
        return "openai"
    if "claude" in lower:
        return "anthropic"
    if "gemini" in lower:
        return "google"
    if "command" in lower or "coral" in lower:
        return "cohere"
    if "llama" in lower or "mixtral" in lower or "mistral" in lower:
        return "meta"
    return "unknown"


def _parse_json(raw: str) -> dict[str, Any]:
    """Parse JSON safely, returning empty dict on failure."""
    try:
        result = json.loads(raw)
        if isinstance(result, dict):
            return result
        return {}
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}


def _to_float_or_none(value: Any) -> float | None:
    """Convert value to float or return None."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int_or_none(value: Any) -> int | None:
    """Convert value to int or return None."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_content_parts(
    attrs: dict[str, Any], prefix: str
) -> tuple[TextContent | ImageContent, ...]:
    """Parse multimodal content parts from OpenInference indexed attributes.

    Falls back to plain .content string as a single TextContent.
    """
    parts: list[TextContent | ImageContent] = []
    j = 0
    while True:
        type_key = f"{prefix}.contents.{j}.message_content.type"
        content_type = attrs.get(type_key)
        if content_type is None:
            break

        if content_type == "text":
            text_key = f"{prefix}.contents.{j}.message_content.text"
            text = str(attrs.get(text_key, ""))
            parts.append(TextContent(text=text))
        elif content_type == "image":
            url_key = f"{prefix}.contents.{j}.message_content.image.url.url"
            detail_key = f"{prefix}.contents.{j}.message_content.image.url.detail"
            url = str(attrs.get(url_key, ""))
            detail_raw = attrs.get(detail_key)
            detail = str(detail_raw) if detail_raw is not None else None
            parts.append(ImageContent(url=url, detail=detail))

        j += 1

    if not parts:
        # Fall back to plain .content string
        content_key = f"{prefix}.content"
        content_raw = attrs.get(content_key)
        if content_raw is not None:
            parts.append(TextContent(text=str(content_raw)))

    return tuple(parts)


def _parse_tool_calls(attrs: dict[str, Any], prefix: str) -> tuple[ToolCall, ...]:
    """Parse tool calls from OpenInference indexed attributes."""
    tool_calls: list[ToolCall] = []
    j = 0
    while True:
        name_key = f"{prefix}.tool_calls.{j}.tool_call.function.name"
        name = attrs.get(name_key)
        if name is None:
            break

        args_key = f"{prefix}.tool_calls.{j}.tool_call.function.arguments"
        args_raw = attrs.get(args_key)
        if isinstance(args_raw, str):
            try:
                arguments = json.loads(args_raw)
            except json.JSONDecodeError:
                arguments = {"_raw": args_raw}
        elif isinstance(args_raw, dict):
            arguments = args_raw
        else:
            arguments = {}

        id_key = f"{prefix}.tool_calls.{j}.tool_call.id"
        call_id_raw = attrs.get(id_key)
        call_id = str(call_id_raw) if call_id_raw is not None else None

        tool_calls.append(ToolCall(name=str(name), arguments=arguments, id=call_id))
        j += 1

    return tuple(tool_calls)


def _parse_input_messages(attrs: dict[str, Any]) -> list[Message]:
    """Parse input messages from OpenInference indexed span attributes."""
    messages: list[Message] = []
    i = 0
    while True:
        prefix = f"llm.input_messages.{i}.message"
        role_key = f"{prefix}.role"
        role = attrs.get(role_key)
        if role is None:
            break

        role = str(role).lower()

        if role == "system":
            content_key = f"{prefix}.content"
            content = str(attrs.get(content_key, ""))
            messages.append(SystemMessage(content=content))
        elif role == "user":
            parts = _parse_content_parts(attrs, prefix)
            messages.append(UserMessage(content=parts))
        elif role == "assistant":
            parts = _parse_content_parts(attrs, prefix)
            tool_calls = _parse_tool_calls(attrs, prefix)
            messages.append(AssistantMessage(content=parts, tool_calls=tool_calls))
        elif role == "tool":
            content_key = f"{prefix}.content"
            content = str(attrs.get(content_key, ""))
            tool_call_id_raw = attrs.get(f"{prefix}.tool_call_id")
            tool_call_id = str(tool_call_id_raw) if tool_call_id_raw is not None else None
            tool_name_raw = attrs.get(f"{prefix}.name")
            tool_name = str(tool_name_raw) if tool_name_raw is not None else None
            messages.append(
                ToolResultMessage(content=content, tool_call_id=tool_call_id, tool_name=tool_name)
            )

        i += 1

    return messages


def _parse_output_messages(attrs: dict[str, Any]) -> list[AssistantMessage]:
    """Parse output messages from OpenInference indexed span attributes."""
    messages: list[AssistantMessage] = []
    i = 0
    while True:
        prefix = f"llm.output_messages.{i}.message"
        role_key = f"{prefix}.role"
        role = attrs.get(role_key)
        if role is None:
            break

        parts = _parse_content_parts(attrs, prefix)
        tool_calls = _parse_tool_calls(attrs, prefix)

        # finish_reason is per-message in OpenInference
        finish_reason_raw = attrs.get(f"{prefix}.finish_reason")
        finish_reason = str(finish_reason_raw) if finish_reason_raw is not None else None

        messages.append(
            AssistantMessage(
                content=parts,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
            )
        )
        i += 1

    return messages


def _parse_tool_definitions(attrs: dict[str, Any]) -> list[ToolDefinition]:
    """Parse tool definitions from OpenInference indexed span attributes."""
    tools: list[ToolDefinition] = []
    i = 0
    while True:
        name_key = f"llm.tools.{i}.tool.name"
        name = attrs.get(name_key)
        if name is None:
            break

        desc_raw = attrs.get(f"llm.tools.{i}.tool.description")
        description = str(desc_raw) if desc_raw is not None else None

        schema_raw = attrs.get(f"llm.tools.{i}.tool.json_schema")
        if isinstance(schema_raw, str):
            parameters = _parse_json(schema_raw) or None
        elif isinstance(schema_raw, dict):
            parameters = schema_raw
        else:
            parameters = None

        tools.append(
            ToolDefinition(name=str(name), description=description, parameters=parameters)
        )
        i += 1

    return tools


# ── Instrumentors ─────────────────────────────────────────────────────────────


_KNOWN_INSTRUMENTORS = [
    ("openinference.instrumentation.openai", "OpenAIInstrumentor"),
    ("openinference.instrumentation.anthropic", "AnthropicInstrumentor"),
    ("openinference.instrumentation.langchain", "LangChainInstrumentor"),
    ("openinference.instrumentation.google_genai", "GoogleGenAIInstrumentor"),
    ("openinference.instrumentation.dspy", "DSPyInstrumentor"),
    # OTel official OpenAI v2 as secondary fallback
    ("opentelemetry.instrumentation.openai_v2", "OpenAIInstrumentor"),
]


def _activate_instrumentors() -> list[str]:
    """Try to instrument all known LLM providers. Returns list of activated names."""
    activated: list[str] = []
    for module_path, class_name in _KNOWN_INSTRUMENTORS:
        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            cls().instrument()
            activated.append(class_name)
            logger.debug("Activated instrumentor: %s from %s", class_name, module_path)
        except ImportError:
            logger.debug(
                "Instrumentor not available (package not installed): %s", module_path
            )
        except Exception:
            logger.debug(
                "Instrumentor failed to activate: %s from %s",
                class_name,
                module_path,
                exc_info=True,
            )
    if not activated:
        logger.warning(
            "No LLM instrumentors activated. Install provider packages "
            "(e.g. openinference-instrumentation-openai) for auto-capture."
        )
    return activated


# ── Observation / initialization ──────────────────────────────────────────────


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


def enable_llm_tracing(
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


def flush(timeout_seconds: float = 5.0) -> bool:
    """Flush the delivery queue, blocking until all items are processed."""
    if _state.delivery_queue is not None:
        return _state.delivery_queue.flush(timeout_seconds=timeout_seconds)
    return True
