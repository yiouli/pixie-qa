"""Tests for pixie.instrumentation.spans — data model types."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from pixie.instrumentation.llm_tracing import (
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


class TestTextContent:
    """Tests for TextContent."""

    def test_fields(self) -> None:
        tc = TextContent(text="hello")
        assert tc.text == "hello"
        assert tc.type == "text"

    def test_frozen(self) -> None:
        tc = TextContent(text="hello")
        with pytest.raises(AttributeError):
            tc.text = "mutated"  # type: ignore[misc]


class TestImageContent:
    """Tests for ImageContent."""

    def test_fields(self) -> None:
        ic = ImageContent(url="https://example.com/img.png", detail="high")
        assert ic.url == "https://example.com/img.png"
        assert ic.detail == "high"
        assert ic.type == "image"

    def test_detail_defaults_to_none(self) -> None:
        ic = ImageContent(url="data:image/png;base64,...")
        assert ic.detail is None


class TestToolCall:
    """Tests for ToolCall."""

    def test_arguments_is_dict(self) -> None:
        tc = ToolCall(name="search", arguments={"query": "hello"})
        assert isinstance(tc.arguments, dict)
        assert tc.arguments == {"query": "hello"}

    def test_id_defaults_to_none(self) -> None:
        tc = ToolCall(name="search", arguments={})
        assert tc.id is None

    def test_frozen(self) -> None:
        tc = ToolCall(name="search", arguments={})
        with pytest.raises(AttributeError):
            tc.name = "mutated"  # type: ignore[misc]


class TestToolDefinition:
    """Tests for ToolDefinition."""

    def test_fields(self) -> None:
        td = ToolDefinition(
            name="search",
            description="Search the web",
            parameters={"type": "object", "properties": {"q": {"type": "string"}}},
        )
        assert td.name == "search"
        assert td.description == "Search the web"
        assert td.parameters is not None

    def test_optional_defaults(self) -> None:
        td = ToolDefinition(name="noop")
        assert td.description is None
        assert td.parameters is None


class TestSystemMessage:
    """Tests for SystemMessage."""

    def test_fields(self) -> None:
        msg = SystemMessage(content="You are helpful.")
        assert msg.content == "You are helpful."
        assert msg.role == "system"


class TestUserMessage:
    """Tests for UserMessage."""

    def test_from_text_creates_single_text_content(self) -> None:
        msg = UserMessage.from_text("hello")
        assert msg.content == (TextContent(text="hello"),)
        assert msg.role == "user"

    def test_multimodal_content(self) -> None:
        msg = UserMessage(
            content=(
                TextContent(text="What's this?"),
                ImageContent(url="https://example.com/img.png"),
            )
        )
        assert len(msg.content) == 2
        assert isinstance(msg.content[0], TextContent)
        assert isinstance(msg.content[1], ImageContent)


class TestAssistantMessage:
    """Tests for AssistantMessage."""

    def test_text_response(self) -> None:
        msg = AssistantMessage(
            content=(TextContent(text="Hello!"),),
            tool_calls=(),
            finish_reason="stop",
        )
        assert msg.role == "assistant"
        assert msg.finish_reason == "stop"

    def test_tool_call_response(self) -> None:
        msg = AssistantMessage(
            content=(),
            tool_calls=(ToolCall(name="search", arguments={"q": "test"}, id="call_1"),),
        )
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].name == "search"


class TestToolResultMessage:
    """Tests for ToolResultMessage."""

    def test_fields(self) -> None:
        msg = ToolResultMessage(
            content='{"result": "found"}',
            tool_call_id="call_1",
            tool_name="search",
        )
        assert msg.role == "tool"
        assert msg.content == '{"result": "found"}'
        assert msg.tool_call_id == "call_1"
        assert msg.tool_name == "search"


class TestObserveSpan:
    """Tests for ObserveSpan."""

    def test_frozen(self) -> None:
        span = ObserveSpan(
            span_id="abc123",
            trace_id="def456",
            parent_span_id=None,
            started_at=datetime.now(tz=timezone.utc),
            ended_at=datetime.now(tz=timezone.utc),
            duration_ms=0.0,
            name="test",
            input=None,
            output=None,
            metadata={},
            error=None,
        )
        with pytest.raises(AttributeError):
            span.name = "mutated"  # type: ignore[misc]

    def test_fields_stored(self) -> None:
        now = datetime.now(tz=timezone.utc)
        span = ObserveSpan(
            span_id="abc",
            trace_id="def",
            parent_span_id="parent",
            started_at=now,
            ended_at=now,
            duration_ms=42.0,
            name="my_block",
            input="question",
            output="answer",
            metadata={"k": "v"},
            error=None,
        )
        assert span.span_id == "abc"
        assert span.parent_span_id == "parent"
        assert span.input == "question"
        assert span.output == "answer"
        assert span.metadata == {"k": "v"}


class TestLLMSpan:
    """Tests for LLMSpan."""

    def _make_llm_span(self, **overrides: Any) -> LLMSpan:
        now = datetime.now(tz=timezone.utc)
        defaults: dict[str, Any] = {
            "span_id": "0000000000000001",
            "trace_id": "00000000000000000000000000000001",
            "parent_span_id": None,
            "started_at": now,
            "ended_at": now,
            "duration_ms": 100.0,
            "operation": "chat",
            "provider": "openai",
            "request_model": "gpt-4",
            "response_model": "gpt-4-0613",
            "input_tokens": 10,
            "output_tokens": 20,
            "cache_read_tokens": 0,
            "cache_creation_tokens": 0,
            "request_temperature": 0.7,
            "request_max_tokens": 1000,
            "request_top_p": 1.0,
            "finish_reasons": ("stop",),
            "response_id": "resp_123",
            "output_type": None,
            "error_type": None,
            "input_messages": (),
            "output_messages": (),
            "tool_definitions": (),
        }
        defaults.update(overrides)
        return LLMSpan(**defaults)

    def test_frozen(self) -> None:
        span = self._make_llm_span()
        with pytest.raises(AttributeError):
            span.request_model = "mutated"  # type: ignore[misc]

    def test_identity_fields(self) -> None:
        span = self._make_llm_span(
            span_id="abcdef0123456789",
            trace_id="abcdef0123456789abcdef0123456789",
            parent_span_id="1234567890abcdef",
        )
        assert span.span_id == "abcdef0123456789"
        assert span.trace_id == "abcdef0123456789abcdef0123456789"
        assert span.parent_span_id == "1234567890abcdef"

    def test_token_defaults(self) -> None:
        span = self._make_llm_span(
            input_tokens=0,
            output_tokens=0,
            cache_read_tokens=0,
            cache_creation_tokens=0,
        )
        assert span.input_tokens == 0
        assert span.output_tokens == 0
        assert span.cache_read_tokens == 0
        assert span.cache_creation_tokens == 0
