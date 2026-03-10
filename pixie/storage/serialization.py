"""Span serialization and deserialization for database storage.

Handles conversion between frozen dataclass span instances and dict
representations suitable for Piccolo table rows, including nested types,
tuples, and datetimes.
"""

from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone
from typing import Any

from pixie.instrumentation.spans import (
    AssistantMessage,
    ImageContent,
    LLMSpan,
    ObserveSpan,
    SystemMessage,
    TextContent,
    ToolCall,
    ToolDefinition,
    ToolResultMessage,
    UserMessage,
)


def serialize_span(span: ObserveSpan | LLMSpan) -> dict[str, Any]:
    """Convert a span to a dict matching Observation table columns.

    Returns a dict with keys: ``id``, ``trace_id``, ``parent_span_id``,
    ``span_kind``, ``name``, ``data``, ``error``, ``started_at``,
    ``ended_at``, ``duration_ms``.
    """
    data = _dataclass_to_dict(span)

    if isinstance(span, LLMSpan):
        return {
            "id": span.span_id,
            "trace_id": span.trace_id,
            "parent_span_id": span.parent_span_id,
            "span_kind": "llm",
            "name": span.request_model,
            "data": data,
            "error": span.error_type,
            "started_at": span.started_at,
            "ended_at": span.ended_at,
            "duration_ms": span.duration_ms,
        }

    # ObserveSpan
    return {
        "id": span.span_id,
        "trace_id": span.trace_id,
        "parent_span_id": span.parent_span_id,
        "span_kind": "observe",
        "name": span.name,
        "data": data,
        "error": span.error,
        "started_at": span.started_at,
        "ended_at": span.ended_at,
        "duration_ms": span.duration_ms,
    }


def _dataclass_to_dict(obj: Any) -> Any:
    """Recursively convert a dataclass to a JSON-safe dict.

    - Frozen dataclass → dict (via field introspection, not ``asdict``)
    - ``tuple`` → ``list``
    - ``datetime`` → ISO 8601 string
    - Other primitives pass through unchanged.
    """
    if obj is None:
        return None
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, tuple):
        return [_dataclass_to_dict(item) for item in obj]
    if isinstance(obj, list):
        return [_dataclass_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    # Dataclass
    if hasattr(obj, "__dataclass_fields__"):
        return {f.name: _dataclass_to_dict(getattr(obj, f.name)) for f in fields(obj)}
    return obj  # pragma: no cover


def deserialize_span(row: dict[str, Any]) -> ObserveSpan | LLMSpan:
    """Reconstruct a span from a table row dict.

    The ``span_kind`` field determines the target type. The ``data`` field
    contains the full nested payload.
    """
    kind = row["span_kind"]
    data: dict[str, Any] = row["data"]

    if kind == "llm":
        return _deserialize_llm(data)
    return _deserialize_observe(data)


def _deserialize_observe(data: dict[str, Any]) -> ObserveSpan:
    """Reconstruct an ObserveSpan from serialized data."""
    return ObserveSpan(
        span_id=data["span_id"],
        trace_id=data["trace_id"],
        parent_span_id=data["parent_span_id"],
        started_at=_parse_datetime(data["started_at"]),
        ended_at=_parse_datetime(data["ended_at"]),
        duration_ms=data["duration_ms"],
        name=data["name"],
        input=data["input"],
        output=data["output"],
        metadata=data["metadata"],
        error=data["error"],
    )


def _deserialize_llm(data: dict[str, Any]) -> LLMSpan:
    """Reconstruct an LLMSpan from serialized data."""
    return LLMSpan(
        span_id=data["span_id"],
        trace_id=data["trace_id"],
        parent_span_id=data["parent_span_id"],
        started_at=_parse_datetime(data["started_at"]),
        ended_at=_parse_datetime(data["ended_at"]),
        duration_ms=data["duration_ms"],
        operation=data["operation"],
        provider=data["provider"],
        request_model=data["request_model"],
        response_model=data["response_model"],
        input_tokens=data["input_tokens"],
        output_tokens=data["output_tokens"],
        cache_read_tokens=data["cache_read_tokens"],
        cache_creation_tokens=data["cache_creation_tokens"],
        request_temperature=data["request_temperature"],
        request_max_tokens=data["request_max_tokens"],
        request_top_p=data["request_top_p"],
        finish_reasons=tuple(data["finish_reasons"]),
        response_id=data["response_id"],
        output_type=data["output_type"],
        error_type=data["error_type"],
        input_messages=tuple(_deserialize_message(m) for m in data["input_messages"]),
        output_messages=tuple(_deserialize_assistant_message(m) for m in data["output_messages"]),
        tool_definitions=tuple(
            _deserialize_tool_definition(td) for td in data["tool_definitions"]
        ),
    )


# ── Message deserialization ───────────────────────────────────────────────────


def _deserialize_message(
    m: dict[str, Any],
) -> SystemMessage | UserMessage | AssistantMessage | ToolResultMessage:
    """Dispatch on ``role`` to reconstruct the right message type."""
    role = m["role"]
    if role == "system":
        return SystemMessage(content=m["content"])
    if role == "user":
        return UserMessage(
            content=tuple(_deserialize_content(c) for c in m["content"]),
        )
    if role == "assistant":
        return _deserialize_assistant_message(m)
    if role == "tool":
        return ToolResultMessage(
            content=m["content"],
            tool_call_id=m.get("tool_call_id"),
            tool_name=m.get("tool_name"),
        )
    raise ValueError(f"Unknown message role: {role}")  # pragma: no cover


def _deserialize_assistant_message(m: dict[str, Any]) -> AssistantMessage:
    """Reconstruct an AssistantMessage with content and tool calls."""
    return AssistantMessage(
        content=tuple(_deserialize_content(c) for c in m["content"]),
        tool_calls=tuple(_deserialize_tool_call(tc) for tc in m["tool_calls"]),
        finish_reason=m.get("finish_reason"),
    )


def _deserialize_content(c: dict[str, Any]) -> TextContent | ImageContent:
    """Dispatch on ``type`` to reconstruct the right content type."""
    ctype = c["type"]
    if ctype == "text":
        return TextContent(text=c["text"])
    if ctype == "image":
        return ImageContent(url=c["url"], detail=c.get("detail"))
    raise ValueError(f"Unknown content type: {ctype}")  # pragma: no cover


def _deserialize_tool_call(tc: dict[str, Any]) -> ToolCall:
    """Reconstruct a ToolCall."""
    return ToolCall(
        name=tc["name"],
        arguments=tc["arguments"],
        id=tc.get("id"),
    )


def _deserialize_tool_definition(td: dict[str, Any]) -> ToolDefinition:
    """Reconstruct a ToolDefinition."""
    return ToolDefinition(
        name=td["name"],
        description=td.get("description"),
        parameters=td.get("parameters"),
    )


# ── Utilities ─────────────────────────────────────────────────────────────────


def _parse_datetime(value: str | datetime) -> datetime:
    """Parse an ISO 8601 string to a timezone-aware datetime."""
    if isinstance(value, datetime):
        return value
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
