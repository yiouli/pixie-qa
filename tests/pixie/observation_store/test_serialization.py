"""Tests for pixie.storage.serialization — round-trip span serialization."""

from __future__ import annotations

from datetime import datetime, timezone

from pixie.instrumentation.spans import (
    AssistantMessage,
    LLMSpan,
    ObserveSpan,
    SystemMessage,
    TextContent,
    ToolCall,
    ToolDefinition,
    ToolResultMessage,
    UserMessage,
)
from pixie.storage.serialization import deserialize_span, serialize_span


class TestObserveSpanRoundTrip:
    """Round-trip tests for ObserveSpan serialization."""

    def test_basic_round_trip(self, sample_observe_span: ObserveSpan) -> None:
        row = serialize_span(sample_observe_span)
        restored = deserialize_span(row)
        assert restored == sample_observe_span

    def test_none_input_output(self, sample_observe_span_none_io: ObserveSpan) -> None:
        row = serialize_span(sample_observe_span_none_io)
        restored = deserialize_span(row)
        assert restored == sample_observe_span_none_io

    def test_complex_nested_input(self) -> None:
        span = ObserveSpan(
            span_id="aaaa000000000099",
            trace_id="bbbb0000000000000000000000000099",
            parent_span_id=None,
            started_at=datetime(2025, 6, 15, 10, 30, 0, tzinfo=timezone.utc),
            ended_at=datetime(2025, 6, 15, 10, 30, 1, tzinfo=timezone.utc),
            duration_ms=1000.0,
            name="complex",
            input={"nested": {"list": [1, 2, 3], "dict": {"a": "b"}}},
            output=[{"result": True}, {"result": False}],
            metadata={"key": "value"},
            error=None,
        )
        row = serialize_span(span)
        restored = deserialize_span(row)
        assert restored == span

    def test_column_mapping(self, sample_observe_span: ObserveSpan) -> None:
        row = serialize_span(sample_observe_span)
        assert row["id"] == "aaaa000000000001"
        assert row["span_kind"] == "observe"
        assert row["name"] == "root_pipeline"
        assert row["error"] is None
        assert row["duration_ms"] == 1000.0


class TestLLMSpanRoundTrip:
    """Round-trip tests for LLMSpan serialization."""

    def test_basic_round_trip(self, sample_llm_span: LLMSpan) -> None:
        row = serialize_span(sample_llm_span)
        restored = deserialize_span(row)
        assert restored == sample_llm_span

    def test_with_tool_calls(self, sample_llm_span_with_tools: LLMSpan) -> None:
        row = serialize_span(sample_llm_span_with_tools)
        restored = deserialize_span(row)
        assert restored == sample_llm_span_with_tools

    def test_with_image_content(self, sample_llm_span_with_image: LLMSpan) -> None:
        row = serialize_span(sample_llm_span_with_image)
        restored = deserialize_span(row)
        assert restored == sample_llm_span_with_image

    def test_empty_output_messages(self, sample_llm_span_empty_output: LLMSpan) -> None:
        row = serialize_span(sample_llm_span_empty_output)
        restored = deserialize_span(row)
        assert restored == sample_llm_span_empty_output

    def test_column_mapping(self, sample_llm_span: LLMSpan) -> None:
        row = serialize_span(sample_llm_span)
        assert row["id"] == "aaaa000000000002"
        assert row["span_kind"] == "llm"
        assert row["name"] == "gpt-4o"
        assert row["error"] is None

    def test_tuples_preserved(self, sample_llm_span: LLMSpan) -> None:
        """Tuples should serialize to lists and deserialize back to tuples."""
        row = serialize_span(sample_llm_span)
        # In serialized form, tuples are lists
        assert isinstance(row["data"]["finish_reasons"], list)
        # After deserialization, they're tuples again
        restored = deserialize_span(row)
        assert isinstance(restored, LLMSpan)
        assert isinstance(restored.finish_reasons, tuple)
        assert isinstance(restored.input_messages, tuple)
        assert isinstance(restored.output_messages, tuple)

    def test_datetimes_preserved(self, sample_llm_span: LLMSpan) -> None:
        """Datetimes should serialize to ISO strings and back."""
        row = serialize_span(sample_llm_span)
        assert isinstance(row["data"]["started_at"], str)
        restored = deserialize_span(row)
        assert isinstance(restored, LLMSpan)
        assert restored.started_at == sample_llm_span.started_at
        assert restored.ended_at == sample_llm_span.ended_at

    def test_messages_with_all_roles(self) -> None:
        """Test round-trip with system, user, assistant, and tool messages."""
        span = LLMSpan(
            span_id="aaaa000000000088",
            trace_id="bbbb0000000000000000000000000088",
            parent_span_id=None,
            started_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            ended_at=datetime(2025, 1, 1, 12, 0, 1, tzinfo=timezone.utc),
            duration_ms=1000.0,
            operation="chat",
            provider="openai",
            request_model="gpt-4o",
            response_model="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            request_temperature=0.5,
            request_max_tokens=512,
            request_top_p=0.9,
            finish_reasons=("stop",),
            response_id="resp-1",
            output_type="text",
            error_type=None,
            input_messages=(
                SystemMessage(content="Be helpful."),
                UserMessage.from_text("Hello"),
                ToolResultMessage(
                    content="result data",
                    tool_call_id="tc-1",
                    tool_name="lookup",
                ),
            ),
            output_messages=(
                AssistantMessage(
                    content=(TextContent(text="Hi!"),),
                    tool_calls=(
                        ToolCall(name="lookup", arguments={"q": "x"}, id="tc-1"),
                    ),
                    finish_reason="stop",
                ),
            ),
            tool_definitions=(
                ToolDefinition(name="lookup", description="Look up data"),
            ),
        )
        row = serialize_span(span)
        restored = deserialize_span(row)
        assert restored == span
