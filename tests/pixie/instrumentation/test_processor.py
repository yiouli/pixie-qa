"""Tests for pixie.instrumentation.processor — LLMSpanProcessor."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

from opentelemetry.trace import SpanContext, StatusCode
from opentelemetry.trace.status import Status

from pixie.instrumentation.processor import LLMSpanProcessor
from pixie.instrumentation.queue import _DeliveryQueue
from pixie.instrumentation.spans import (
    AssistantMessage,
    ImageContent,
    SystemMessage,
    TextContent,
    ToolDefinition,
    ToolResultMessage,
    UserMessage,
)

from .conftest import RecordingHandler


def _make_mock_span(
    attrs: dict[str, Any],
    *,
    span_id: int = 1,
    trace_id: int = 1,
    parent_span_id: int | None = None,
    start_time: int = 1_000_000_000,
    end_time: int = 1_100_000_000,
    status_code: StatusCode = StatusCode.OK,
) -> MagicMock:
    """Create a mock ReadableSpan with given attributes."""
    mock = MagicMock()
    mock.attributes = attrs
    mock.context = SpanContext(
        trace_id=trace_id,
        span_id=span_id,
        is_remote=False,
    )
    if parent_span_id is not None:
        mock.parent = SpanContext(
            trace_id=trace_id,
            span_id=parent_span_id,
            is_remote=False,
        )
    else:
        mock.parent = None

    mock.start_time = start_time
    mock.end_time = end_time
    mock.status = Status(status_code)
    mock.name = "llm_call"
    return mock


class TestProcessorDetection:
    """Tests for span filtering — only LLM/EMBEDDING spans are processed."""

    def test_non_llm_span_ignored(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span({"openinference.span.kind": "CHAIN"})
        processor.on_end(span)
        q.flush()
        assert len(recording_handler.llm_spans) == 0

    def test_no_span_kind_ignored(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span({})
        processor.on_end(span)
        q.flush()
        assert len(recording_handler.llm_spans) == 0

    def test_llm_span_processed(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span(
            {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4",
            }
        )
        processor.on_end(span)
        q.flush()
        assert len(recording_handler.llm_spans) == 1

    def test_embedding_span_processed(
        self, recording_handler: RecordingHandler
    ) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span(
            {
                "openinference.span.kind": "EMBEDDING",
                "llm.model_name": "text-embedding-ada-002",
            }
        )
        processor.on_end(span)
        q.flush()
        assert len(recording_handler.llm_spans) == 1
        assert recording_handler.llm_spans[0].operation == "embedding"


class TestProcessorIdentity:
    """Tests for span identity extraction."""

    def test_span_id_and_trace_id(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span(
            {"openinference.span.kind": "LLM", "llm.model_name": "gpt-4"},
            span_id=0xABCDEF0123456789,
            trace_id=0xABCDEF0123456789ABCDEF0123456789,
        )
        processor.on_end(span)
        q.flush()

        llm = recording_handler.llm_spans[0]
        assert llm.span_id == "abcdef0123456789"
        assert llm.trace_id == "abcdef0123456789abcdef0123456789"

    def test_parent_span_id(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span(
            {"openinference.span.kind": "LLM", "llm.model_name": "gpt-4"},
            parent_span_id=0x1234567890ABCDEF,
        )
        processor.on_end(span)
        q.flush()

        llm = recording_handler.llm_spans[0]
        assert llm.parent_span_id == "1234567890abcdef"

    def test_no_parent_span_id(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span(
            {"openinference.span.kind": "LLM", "llm.model_name": "gpt-4"},
        )
        processor.on_end(span)
        q.flush()

        llm = recording_handler.llm_spans[0]
        assert llm.parent_span_id is None


class TestProcessorTokenUsage:
    """Tests for token usage extraction."""

    def test_token_counts(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span(
            {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4",
                "llm.token_count.prompt": 100,
                "llm.token_count.completion": 50,
                "llm.token_count.cache_read": 30,
                "llm.token_count.cache_creation": 10,
            }
        )
        processor.on_end(span)
        q.flush()

        llm = recording_handler.llm_spans[0]
        assert llm.input_tokens == 100
        assert llm.output_tokens == 50
        assert llm.cache_read_tokens == 30
        assert llm.cache_creation_tokens == 10

    def test_missing_tokens_default_to_zero(
        self, recording_handler: RecordingHandler
    ) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span(
            {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4",
            }
        )
        processor.on_end(span)
        q.flush()

        llm = recording_handler.llm_spans[0]
        assert llm.input_tokens == 0
        assert llm.output_tokens == 0


class TestProcessorRequestParams:
    """Tests for request parameter parsing from invocation_parameters."""

    def test_invocation_parameters_parsed(
        self, recording_handler: RecordingHandler
    ) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        params = json.dumps(
            {
                "temperature": 0.5,
                "max_tokens": 1024,
                "top_p": 0.9,
            }
        )
        span = _make_mock_span(
            {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4",
                "llm.invocation_parameters": params,
            }
        )
        processor.on_end(span)
        q.flush()

        llm = recording_handler.llm_spans[0]
        assert llm.request_temperature == 0.5
        assert llm.request_max_tokens == 1024
        assert llm.request_top_p == 0.9

    def test_max_completion_tokens_fallback(
        self, recording_handler: RecordingHandler
    ) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        params = json.dumps({"max_completion_tokens": 2048})
        span = _make_mock_span(
            {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4",
                "llm.invocation_parameters": params,
            }
        )
        processor.on_end(span)
        q.flush()

        assert recording_handler.llm_spans[0].request_max_tokens == 2048

    def test_malformed_json_fallback(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span(
            {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4",
                "llm.invocation_parameters": "not-json{",
            }
        )
        processor.on_end(span)
        q.flush()

        llm = recording_handler.llm_spans[0]
        assert llm.request_temperature is None
        assert llm.request_max_tokens is None


class TestProcessorInputMessages:
    """Tests for input message parsing."""

    def test_basic_text_conversation(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span(
            {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4",
                "llm.input_messages.0.message.role": "system",
                "llm.input_messages.0.message.content": "You are helpful.",
                "llm.input_messages.1.message.role": "user",
                "llm.input_messages.1.message.content": "Hello!",
            }
        )
        processor.on_end(span)
        q.flush()

        llm = recording_handler.llm_spans[0]
        assert len(llm.input_messages) == 2
        assert isinstance(llm.input_messages[0], SystemMessage)
        assert llm.input_messages[0].content == "You are helpful."
        assert isinstance(llm.input_messages[1], UserMessage)
        assert llm.input_messages[1].content == (TextContent(text="Hello!"),)

    def test_multimodal_user_message(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span(
            {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4",
                "llm.input_messages.0.message.role": "user",
                "llm.input_messages.0.message.contents.0.message_content.type": "text",
                "llm.input_messages.0.message.contents.0.message_content.text": "What is this?",
                "llm.input_messages.0.message.contents.1.message_content.type": "image",
                "llm.input_messages.0.message.contents.1.message_content.image.url.url": "https://example.com/img.png",
                "llm.input_messages.0.message.contents.1.message_content.image.url.detail": "high",
            }
        )
        processor.on_end(span)
        q.flush()

        llm = recording_handler.llm_spans[0]
        user_msg = llm.input_messages[0]
        assert isinstance(user_msg, UserMessage)
        assert len(user_msg.content) == 2
        assert isinstance(user_msg.content[0], TextContent)
        assert isinstance(user_msg.content[1], ImageContent)
        assert user_msg.content[1].url == "https://example.com/img.png"
        assert user_msg.content[1].detail == "high"

    def test_tool_result_message(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span(
            {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4",
                "llm.input_messages.0.message.role": "tool",
                "llm.input_messages.0.message.content": '{"result": "42"}',
                "llm.input_messages.0.message.tool_call_id": "call_123",
                "llm.input_messages.0.message.name": "calculator",
            }
        )
        processor.on_end(span)
        q.flush()

        llm = recording_handler.llm_spans[0]
        msg = llm.input_messages[0]
        assert isinstance(msg, ToolResultMessage)
        assert msg.content == '{"result": "42"}'
        assert msg.tool_call_id == "call_123"
        assert msg.tool_name == "calculator"


class TestProcessorOutputMessages:
    """Tests for output message parsing."""

    def test_text_output(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span(
            {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4",
                "llm.output_messages.0.message.role": "assistant",
                "llm.output_messages.0.message.content": "Hello!",
                "llm.output_messages.0.message.finish_reason": "stop",
            }
        )
        processor.on_end(span)
        q.flush()

        llm = recording_handler.llm_spans[0]
        assert len(llm.output_messages) == 1
        assert isinstance(llm.output_messages[0], AssistantMessage)
        assert llm.output_messages[0].content == (TextContent(text="Hello!"),)
        assert llm.output_messages[0].finish_reason == "stop"

    def test_tool_call_in_output(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span(
            {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4",
                "llm.output_messages.0.message.role": "assistant",
                "llm.output_messages.0.message.tool_calls.0.tool_call.function.name": "search",
                "llm.output_messages.0.message.tool_calls.0.tool_call.function.arguments": (
                    '{"query": "test"}'
                ),
                "llm.output_messages.0.message.tool_calls.0.tool_call.id": "call_abc",
                "llm.output_messages.0.message.finish_reason": "tool_calls",
            }
        )
        processor.on_end(span)
        q.flush()

        llm = recording_handler.llm_spans[0]
        msg = llm.output_messages[0]
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].name == "search"
        assert msg.tool_calls[0].arguments == {"query": "test"}
        assert msg.tool_calls[0].id == "call_abc"

    def test_finish_reasons_collected(
        self, recording_handler: RecordingHandler
    ) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span(
            {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4",
                "llm.output_messages.0.message.role": "assistant",
                "llm.output_messages.0.message.content": "Done.",
                "llm.output_messages.0.message.finish_reason": "stop",
            }
        )
        processor.on_end(span)
        q.flush()

        llm = recording_handler.llm_spans[0]
        assert llm.finish_reasons == ("stop",)

    def test_malformed_tool_call_arguments(
        self, recording_handler: RecordingHandler
    ) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span(
            {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4",
                "llm.output_messages.0.message.role": "assistant",
                "llm.output_messages.0.message.tool_calls.0.tool_call.function.name": "search",
                (
                    "llm.output_messages.0.message.tool_calls.0.tool_call.function.arguments"
                ): "bad{json",
            }
        )
        processor.on_end(span)
        q.flush()

        msg = recording_handler.llm_spans[0].output_messages[0]
        assert msg.tool_calls[0].arguments == {"_raw": "bad{json"}


class TestProcessorToolDefinitions:
    """Tests for tool definition parsing."""

    def test_tool_definitions_parsed(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        schema = json.dumps({"type": "object", "properties": {"q": {"type": "string"}}})
        span = _make_mock_span(
            {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4",
                "llm.tools.0.tool.name": "search",
                "llm.tools.0.tool.description": "Search the web",
                "llm.tools.0.tool.json_schema": schema,
            }
        )
        processor.on_end(span)
        q.flush()

        llm = recording_handler.llm_spans[0]
        assert len(llm.tool_definitions) == 1
        td = llm.tool_definitions[0]
        assert isinstance(td, ToolDefinition)
        assert td.name == "search"
        assert td.description == "Search the web"
        assert td.parameters == {
            "type": "object",
            "properties": {"q": {"type": "string"}},
        }


class TestProcessorProviderInference:
    """Tests for provider inference from model name."""

    def test_openai_model(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span(
            {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4-turbo",
            }
        )
        processor.on_end(span)
        q.flush()
        assert recording_handler.llm_spans[0].provider == "openai"

    def test_anthropic_model(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span(
            {
                "openinference.span.kind": "LLM",
                "llm.model_name": "claude-3-opus",
            }
        )
        processor.on_end(span)
        q.flush()
        assert recording_handler.llm_spans[0].provider == "anthropic"

    def test_explicit_gen_ai_system(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span(
            {
                "openinference.span.kind": "LLM",
                "llm.model_name": "custom-model",
                "gen_ai.system": "azure",
            }
        )
        processor.on_end(span)
        q.flush()
        assert recording_handler.llm_spans[0].provider == "azure"


class TestProcessorErrorHandling:
    """Tests for error type extraction and processor safety."""

    def test_error_type_from_attribute(
        self, recording_handler: RecordingHandler
    ) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span(
            {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4",
                "error.type": "RateLimitError",
            }
        )
        processor.on_end(span)
        q.flush()
        assert recording_handler.llm_spans[0].error_type == "RateLimitError"

    def test_error_type_from_status(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        span = _make_mock_span(
            {"openinference.span.kind": "LLM", "llm.model_name": "gpt-4"},
            status_code=StatusCode.ERROR,
        )
        processor.on_end(span)
        q.flush()
        assert recording_handler.llm_spans[0].error_type == "error"

    def test_processor_never_raises(self, recording_handler: RecordingHandler) -> None:
        """Even with completely broken span data, processor doesn't raise."""
        q = _DeliveryQueue(recording_handler, maxsize=10)
        processor = LLMSpanProcessor(q)

        # Span with no context at all
        broken_span = MagicMock()
        broken_span.attributes = {"openinference.span.kind": "LLM"}
        broken_span.context = None  # This will cause AttributeError
        # Should not raise
        processor.on_end(broken_span)
