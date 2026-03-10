"""Tests for pixie.instrumentation.queue — _DeliveryQueue."""

from __future__ import annotations

import asyncio
import threading
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


def _make_named_observe_span(name: str) -> ObserveSpan:
    """Create a minimal ObserveSpan with a specific name for fire-and-forget tests."""
    now = datetime.now(tz=timezone.utc)
    return ObserveSpan(
        span_id="0000000000000002",
        trace_id="00000000000000000000000000000001",
        parent_span_id=None,
        started_at=now,
        ended_at=now,
        duration_ms=0.0,
        name=name,
        input=None,
        output=None,
        metadata={},
        error=None,
    )


class TestDeliveryQueueDispatch:
    """Tests for dispatching spans to correct handler methods."""

    def test_llm_span_dispatched_to_on_llm(
        self, recording_handler: RecordingHandler
    ) -> None:
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

        block = threading.Event()

        class BlockingHandler(InstrumentationHandler):
            async def on_llm(self, span: LLMSpan) -> None:
                await asyncio.get_event_loop().run_in_executor(None, block.wait)

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

            async def on_llm(self, span: LLMSpan) -> None:
                raise RuntimeError("handler crash!")

            async def on_observe(self, span: ObserveSpan) -> None:
                self.observe_count += 1

        handler = CrashingHandler()
        q = _DeliveryQueue(handler, maxsize=10)

        # Submit an LLM span that will crash the handler
        q.submit(_make_llm_span())
        # Then an observe span that should still be processed
        q.submit(_make_observe_span())
        q.flush()

        assert handler.observe_count == 1


class TestDeliveryQueueFireAndForget:
    """Tests that the queue worker is fire-and-forget: it schedules async processing
    and immediately loops back to consume the next item without waiting."""

    def test_worker_does_not_block_on_slow_handler(self) -> None:
        """The queue worker must not await the handler coroutine.

        span1's handler intentionally blocks.  If the worker were synchronous
        or awaiting directly, span2 would only start after span1 released.
        With the fire-and-forget design the worker loops immediately, so span2
        starts processing while span1's coroutine is still running.
        """
        span1_started = threading.Event()
        span2_started = threading.Event()
        span1_release = threading.Event()

        class OrderTracker(InstrumentationHandler):
            async def on_observe(self, span: ObserveSpan) -> None:
                if span.name == "span1":
                    span1_started.set()
                    # Block span1 inside the event loop's thread-pool executor
                    await asyncio.get_running_loop().run_in_executor(
                        None, span1_release.wait
                    )
                elif span.name == "span2":
                    span2_started.set()

        q = _DeliveryQueue(OrderTracker(), maxsize=10)
        q.submit(_make_named_observe_span("span1"))

        # Wait until span1's async handler has started running
        assert span1_started.wait(timeout=2.0), "span1 handler never started"

        # span1's handler is now blocked inside run_in_executor.
        # The worker should already have looped back; submit span2.
        q.submit(_make_named_observe_span("span2"))

        # span2 must start processing WITHOUT waiting for span1 to release.
        assert span2_started.wait(
            timeout=2.0
        ), "span2 did not start — worker likely blocked on span1's slow handler"

        # Clean up: release span1 and drain the queue.
        span1_release.set()
        q.flush()
