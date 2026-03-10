"""Data model types for pixie instrumentation spans."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal  # noqa: UP035

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
