"""LLMSpanProcessor — converts OpenInference span attributes to LLMSpan."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor
from opentelemetry.trace import StatusCode

from .queue import _DeliveryQueue
from .spans import (
    AssistantMessage,
    ImageContent,
    LLMSpan,
    Message,
    SystemMessage,
    TextContent,
    ToolCall,
    ToolDefinition,
    ToolResultMessage,
    UserMessage,
)


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

            # Write to trace file if a writer is active
            try:
                from dataclasses import asdict

                from pixie.instrumentation.trace_writer import get_trace_writer

                writer = get_trace_writer()
                if writer is not None:
                    writer.write_llm_span(asdict(llm_span))
            except Exception:
                pass
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


# ── Helper functions ──────────────────────────────────────────────────────────


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
