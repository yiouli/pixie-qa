"""Shared fixtures for observation_store tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

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


@pytest.fixture
def sample_observe_span() -> ObserveSpan:
    """A minimal ObserveSpan for testing."""
    return ObserveSpan(
        span_id="aaaa000000000001",
        trace_id="bbbb0000000000000000000000000001",
        parent_span_id=None,
        started_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        ended_at=datetime(2025, 1, 1, 12, 0, 1, tzinfo=timezone.utc),
        duration_ms=1000.0,
        name="root_pipeline",
        input={"query": "What is our refund policy?"},
        output="You can return items within 30 days.",
        metadata={"env": "test"},
        error=None,
    )


@pytest.fixture
def sample_llm_span() -> LLMSpan:
    """A fully-populated LLMSpan for testing."""
    return LLMSpan(
        span_id="aaaa000000000002",
        trace_id="bbbb0000000000000000000000000001",
        parent_span_id="aaaa000000000001",
        started_at=datetime(2025, 1, 1, 12, 0, 0, 100000, tzinfo=timezone.utc),
        ended_at=datetime(2025, 1, 1, 12, 0, 0, 450000, tzinfo=timezone.utc),
        duration_ms=350.0,
        operation="chat",
        provider="openai",
        request_model="gpt-4o",
        response_model="gpt-4o-2025-01-01",
        input_tokens=150,
        output_tokens=42,
        cache_read_tokens=30,
        cache_creation_tokens=0,
        request_temperature=0.7,
        request_max_tokens=1024,
        request_top_p=None,
        finish_reasons=("stop",),
        response_id="chatcmpl-123",
        output_type="text",
        error_type=None,
        input_messages=(
            SystemMessage(content="You are a helpful assistant."),
            UserMessage.from_text("What is our refund policy?"),
        ),
        output_messages=(
            AssistantMessage(
                content=(TextContent(text="You can return items within 30 days."),),
                tool_calls=(),
                finish_reason="stop",
            ),
        ),
        tool_definitions=(),
    )


@pytest.fixture
def sample_llm_span_with_tools() -> LLMSpan:
    """An LLMSpan with tool calls, tool definitions, and tool result messages."""
    return LLMSpan(
        span_id="aaaa000000000003",
        trace_id="bbbb0000000000000000000000000001",
        parent_span_id="aaaa000000000001",
        started_at=datetime(2025, 1, 1, 12, 0, 0, 200000, tzinfo=timezone.utc),
        ended_at=datetime(2025, 1, 1, 12, 0, 0, 600000, tzinfo=timezone.utc),
        duration_ms=400.0,
        operation="chat",
        provider="anthropic",
        request_model="claude-3-opus",
        response_model="claude-3-opus-20240229",
        input_tokens=200,
        output_tokens=80,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        request_temperature=None,
        request_max_tokens=2048,
        request_top_p=None,
        finish_reasons=("tool_use",),
        response_id="msg-456",
        output_type=None,
        error_type=None,
        input_messages=(
            SystemMessage(content="You can use tools."),
            UserMessage.from_text("Search for refund policy"),
            ToolResultMessage(
                content="Returns accepted within 30 days",
                tool_call_id="call-1",
                tool_name="search",
            ),
        ),
        output_messages=(
            AssistantMessage(
                content=(TextContent(text="Based on the search results..."),),
                tool_calls=(
                    ToolCall(
                        name="search",
                        arguments={"query": "refund policy"},
                        id="call-1",
                    ),
                ),
                finish_reason="tool_use",
            ),
        ),
        tool_definitions=(
            ToolDefinition(
                name="search",
                description="Search the knowledge base",
                parameters={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
            ),
        ),
    )


@pytest.fixture
def sample_llm_span_with_image() -> LLMSpan:
    """An LLMSpan with ImageContent in a UserMessage."""
    return LLMSpan(
        span_id="aaaa000000000004",
        trace_id="bbbb0000000000000000000000000002",
        parent_span_id=None,
        started_at=datetime(2025, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
        ended_at=datetime(2025, 1, 1, 13, 0, 1, tzinfo=timezone.utc),
        duration_ms=1000.0,
        operation="chat",
        provider="openai",
        request_model="gpt-4o",
        response_model="gpt-4o-2025-01-01",
        input_tokens=500,
        output_tokens=100,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        request_temperature=None,
        request_max_tokens=None,
        request_top_p=None,
        finish_reasons=("stop",),
        response_id=None,
        output_type=None,
        error_type=None,
        input_messages=(
            UserMessage(
                content=(
                    TextContent(text="Describe this image"),
                    ImageContent(url="https://example.com/img.png", detail="high"),
                ),
            ),
        ),
        output_messages=(
            AssistantMessage(
                content=(TextContent(text="The image shows a cat."),),
                tool_calls=(),
                finish_reason="stop",
            ),
        ),
        tool_definitions=(),
    )


@pytest.fixture
def sample_llm_span_empty_output() -> LLMSpan:
    """An LLMSpan with empty output_messages."""
    return LLMSpan(
        span_id="aaaa000000000005",
        trace_id="bbbb0000000000000000000000000002",
        parent_span_id=None,
        started_at=datetime(2025, 1, 1, 14, 0, 0, tzinfo=timezone.utc),
        ended_at=datetime(2025, 1, 1, 14, 0, 0, 500000, tzinfo=timezone.utc),
        duration_ms=500.0,
        operation="chat",
        provider="openai",
        request_model="gpt-4o",
        response_model=None,
        input_tokens=0,
        output_tokens=0,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        request_temperature=None,
        request_max_tokens=None,
        request_top_p=None,
        finish_reasons=(),
        response_id=None,
        output_type=None,
        error_type="TimeoutError",
        input_messages=(UserMessage.from_text("Hello"),),
        output_messages=(),
        tool_definitions=(),
    )


@pytest.fixture
def sample_observe_span_none_io() -> ObserveSpan:
    """An ObserveSpan with None input and output."""
    return ObserveSpan(
        span_id="aaaa000000000006",
        trace_id="bbbb0000000000000000000000000003",
        parent_span_id=None,
        started_at=datetime(2025, 1, 1, 15, 0, 0, tzinfo=timezone.utc),
        ended_at=datetime(2025, 1, 1, 15, 0, 0, 100000, tzinfo=timezone.utc),
        duration_ms=100.0,
        name=None,
        input=None,
        output=None,
        metadata={},
        error=None,
    )
