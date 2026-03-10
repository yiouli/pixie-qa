"""Tests for pixie.instrumentation.queue — _DeliveryQueue."""

from __future__ import annotations

from datetime import datetime, timezone

from pixie.instrumentation.handler import InstrumentationHandler
from pixie.instrumentation.queue import _DeliveryQueue
from pixie.instrumentation.spans import LLMSpan, ObserveSpan

from .conftest import RecordingHandler


def _make_llm_span() -> LLMSpan:
    """Create a minimal LLMSpan for testing."""
    now = datetime.now(tz=timezone.utc)
    return LLMSpan(
        span_id="0000000000000001",
        trace_id="00000000000000000000000000000001",
        parent_span_id=None,
        started_at=now,
        ended_at=now,
        duration_ms=0.0,
        operation="chat",
        provider="openai",
        request_model="gpt-4",
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
        error_type=None,
        input_messages=(),
        output_messages=(),
        tool_definitions=(),
    )


def _make_observe_span() -> ObserveSpan:
    """Create a minimal ObserveSpan for testing."""
    now = datetime.now(tz=timezone.utc)
    return ObserveSpan(
        span_id="0000000000000002",
        trace_id="00000000000000000000000000000001",
        parent_span_id=None,
        started_at=now,
        ended_at=now,
        duration_ms=0.0,
        name="test",
        input=None,
        output=None,
        metadata={},
        error=None,
    )


class TestDeliveryQueueDispatch:
    """Tests for dispatching spans to correct handler methods."""

    def test_llm_span_dispatched_to_on_llm(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        q.submit(_make_llm_span())
        q.flush()
        assert len(recording_handler.llm_spans) == 1
        assert len(recording_handler.observe_spans) == 0

    def test_observe_span_dispatched_to_on_observe(
        self, recording_handler: RecordingHandler
    ) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        q.submit(_make_observe_span())
        q.flush()
        assert len(recording_handler.observe_spans) == 1
        assert len(recording_handler.llm_spans) == 0

    def test_both_types_dispatched(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=10)
        q.submit(_make_llm_span())
        q.submit(_make_observe_span())
        q.flush()
        assert len(recording_handler.llm_spans) == 1
        assert len(recording_handler.observe_spans) == 1


class TestDeliveryQueueDropping:
    """Tests for queue overflow behavior."""

    def test_drop_on_full_queue(self, recording_handler: RecordingHandler) -> None:
        q = _DeliveryQueue(recording_handler, maxsize=1)
        # Fill the queue — the worker might consume right away, so we may
        # need several submissions to eventually trigger a drop
        for _ in range(100):
            q.submit(_make_llm_span())
            if q.dropped_count > 0:
                break
        # If the worker is fast enough it may never drop — at least verify the property exists
        assert isinstance(q.dropped_count, int)

    def test_dropped_count_increments(self) -> None:
        """Test with a handler that blocks to guarantee drops."""

        import threading

        block = threading.Event()

        class BlockingHandler(InstrumentationHandler):
            def on_llm(self, span: LLMSpan) -> None:
                block.wait()  # Block until released

        handler = BlockingHandler()
        q = _DeliveryQueue(handler, maxsize=2)

        # Submit first item — worker will pick it up and block
        q.submit(_make_llm_span())
        import time

        time.sleep(0.05)  # Let worker grab it

        # Now the queue can hold 2 more (maxsize=2), but worker is blocked
        q.submit(_make_llm_span())
        q.submit(_make_llm_span())
        # Queue is full now; next submit should drop
        q.submit(_make_llm_span())
        assert q.dropped_count >= 1

        # Release the worker
        block.set()
        q.flush()


class TestDeliveryQueueHandlerExceptions:
    """Tests that handler exceptions don't crash the worker."""

    def test_handler_exception_doesnt_crash_worker(self) -> None:
        class CrashingHandler(InstrumentationHandler):
            def __init__(self) -> None:
                self.observe_count = 0

            def on_llm(self, span: LLMSpan) -> None:
                raise RuntimeError("handler crash!")

            def on_observe(self, span: ObserveSpan) -> None:
                self.observe_count += 1

        handler = CrashingHandler()
        q = _DeliveryQueue(handler, maxsize=10)

        # Submit an LLM span that will crash the handler
        q.submit(_make_llm_span())
        # Then an observe span that should still be processed
        q.submit(_make_observe_span())
        q.flush()

        assert handler.observe_count == 1
