"""Integration tests for pixie.instrumentation — end-to-end pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock

from opentelemetry.trace import SpanContext, StatusCode
from opentelemetry.trace.status import Status

import pixie.instrumentation as px
from pixie.instrumentation.spans import LLMSpan, ObserveSpan

from .conftest import RecordingHandler


def _inject_fake_llm_span(
    *,
    model: str = "gpt-4",
    parent_span_id: int | None = None,
    trace_id: int = 1,
) -> None:
    """Simulate an OpenInference LLM span being processed by our provider."""
    provider = px._state.tracer_provider
    if provider is None:
        return
    # Access the span processors registered on our provider
    processors = getattr(provider, "_active_span_processor", None)
    if processors is None:
        return

    mock_span = MagicMock()
    mock_span.attributes = {
        "openinference.span.kind": "LLM",
        "llm.model_name": model,
        "llm.token_count.prompt": 10,
        "llm.token_count.completion": 20,
        "llm.output_messages.0.message.role": "assistant",
        "llm.output_messages.0.message.content": "Hello!",
        "llm.output_messages.0.message.finish_reason": "stop",
    }
    mock_span.context = SpanContext(
        trace_id=trace_id,
        span_id=0xABCDEF0123456789,
        is_remote=False,
    )
    if parent_span_id is not None:
        mock_span.parent = SpanContext(
            trace_id=trace_id,
            span_id=parent_span_id,
            is_remote=False,
        )
    else:
        mock_span.parent = None
    mock_span.start_time = 1_000_000_000
    mock_span.end_time = 1_100_000_000
    mock_span.status = Status(StatusCode.OK)
    mock_span.name = "llm_call"

    processors.on_end(mock_span)


class TestInitAndLLMSpan:
    """Tests for init() → fake LLM span → on_llm() called."""

    def test_init_then_llm_span_delivered(self, recording_handler: RecordingHandler) -> None:
        px.init()
        px.add_handler(recording_handler)
        _inject_fake_llm_span(model="gpt-4")
        px.flush()

        assert len(recording_handler.llm_spans) == 1
        llm = recording_handler.llm_spans[0]
        assert isinstance(llm, LLMSpan)
        assert llm.request_model == "gpt-4"
        assert llm.input_tokens == 10
        assert llm.output_tokens == 20


class TestLogObserveSpan:
    """Tests for log() block → on_observe() called."""

    def test_log_delivers_observe_span(self, recording_handler: RecordingHandler) -> None:
        px.init()
        px.add_handler(recording_handler)
        with px.start_observation(input="my question", name="qa") as span:
            span.set_output("my answer")
            span.set_metadata("source", "test")
        px.flush()

        assert len(recording_handler.observe_spans) == 1
        obs = recording_handler.observe_spans[0]
        assert isinstance(obs, ObserveSpan)
        assert obs.input == "my question"
        assert obs.output == "my answer"
        assert obs.metadata == {"source": "test"}
        assert obs.name == "qa"
        assert obs.error is None


class TestLLMInsideLog:
    """Tests for LLM call inside log() → parent_span_id == observe_span.span_id."""

    def test_llm_span_parented_to_observe_span(self, recording_handler: RecordingHandler) -> None:
        px.init()
        px.add_handler(recording_handler)

        with px.start_observation(input="q", name="parent_block") as span:
            # Get the current OTel span's context to use as parent
            otel_span = span._otel_span
            parent_ctx = otel_span.get_span_context()
            _inject_fake_llm_span(
                model="claude-3-opus",
                parent_span_id=parent_ctx.span_id,
                trace_id=parent_ctx.trace_id,
            )
            span.set_output("a")

        px.flush()

        assert len(recording_handler.observe_spans) == 1
        assert len(recording_handler.llm_spans) == 1

        obs = recording_handler.observe_spans[0]
        llm = recording_handler.llm_spans[0]

        # LLM span should have observe span as parent
        assert llm.parent_span_id == obs.span_id
        # They should share the same trace_id
        assert llm.trace_id == obs.trace_id


class TestFlush:
    """Tests for flush()."""

    def test_flush_processes_all_pending(self, recording_handler: RecordingHandler) -> None:
        px.init()
        px.add_handler(recording_handler)

        with px.start_observation(input="q1"):
            pass
        with px.start_observation(input="q2"):
            pass
        _inject_fake_llm_span()

        result = px.flush()
        assert result is True
        assert len(recording_handler.observe_spans) == 2
        assert len(recording_handler.llm_spans) == 1

    def test_flush_without_init_returns_true(self) -> None:
        """Flush on uninitialized state should not error."""
        # State is reset by autouse fixture
        result = px.flush()
        assert result is True


class TestMultipleHandlers:
    """Tests for add_handler/remove_handler with multiple handlers."""

    def test_multiple_handlers_receive_spans(self) -> None:
        handler1 = RecordingHandler()
        handler2 = RecordingHandler()

        px.init()
        px.add_handler(handler1)
        px.add_handler(handler2)
        with px.start_observation(input="q1"):
            pass
        px.flush()

        # Both handlers should have received q1
        assert len(handler1.observe_spans) == 1
        assert handler1.observe_spans[0].input == "q1"
        assert len(handler2.observe_spans) == 1
        assert handler2.observe_spans[0].input == "q1"

    def test_remove_handler_stops_delivery(self) -> None:
        handler1 = RecordingHandler()
        handler2 = RecordingHandler()

        px.init()
        px.add_handler(handler1)
        px.add_handler(handler2)
        with px.start_observation(input="q1"):
            pass
        px.flush()

        # Remove handler1
        px.remove_handler(handler1)
        with px.start_observation(input="q2"):
            pass
        px.flush()

        # handler1 should only have q1
        assert len(handler1.observe_spans) == 1
        assert handler1.observe_spans[0].input == "q1"

        # handler2 should have both
        assert len(handler2.observe_spans) == 2
        assert handler2.observe_spans[1].input == "q2"
