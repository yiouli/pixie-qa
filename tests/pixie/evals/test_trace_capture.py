"""Tests for pixie.evals.trace_capture — MemoryTraceHandler, capture_traces."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

import pixie.instrumentation.observation as px
from pixie.evals.trace_capture import MemoryTraceHandler, capture_traces
from pixie.instrumentation.spans import LLMSpan, ObserveSpan

# ── Helpers ──────────────────────────────────────────────────────────────


def _make_observe_span(
    *,
    span_id: str = "s1",
    trace_id: str = "t1",
    parent_span_id: str | None = None,
    name: str = "test",
) -> ObserveSpan:
    now = datetime.now(tz=timezone.utc)
    return ObserveSpan(
        span_id=span_id,
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        started_at=now,
        ended_at=now,
        duration_ms=1.0,
        name=name,
        input="in",
        output="out",
        metadata={},
        error=None,
    )


def _make_llm_span(
    *,
    span_id: str = "s2",
    trace_id: str = "t1",
    parent_span_id: str | None = "s1",
) -> LLMSpan:
    now = datetime.now(tz=timezone.utc)
    return LLMSpan(
        span_id=span_id,
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        started_at=now,
        ended_at=now,
        duration_ms=2.0,
        operation="chat",
        provider="openai",
        request_model="gpt-4o",
        response_model="gpt-4o",
        input_tokens=10,
        output_tokens=20,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        request_temperature=None,
        request_max_tokens=None,
        request_top_p=None,
        finish_reasons=("stop",),
        response_id=None,
        output_type=None,
        error_type=None,
        input_messages=(),
        output_messages=(),
        tool_definitions=(),
    )


@pytest.fixture(autouse=True)
def _reset_instrumentation() -> None:
    """Reset global instrumentation state before each test."""
    px._reset_state()


# ── MemoryTraceHandler tests ─────────────────────────────────────────────


class TestMemoryTraceHandler:
    """Tests for MemoryTraceHandler span collection."""

    def test_collects_observe_span(self) -> None:
        handler = MemoryTraceHandler()
        span = _make_observe_span()
        asyncio.run(handler.on_observe(span))
        assert handler.spans == [span]

    def test_collects_llm_span(self) -> None:
        handler = MemoryTraceHandler()
        span = _make_llm_span()
        asyncio.run(handler.on_llm(span))
        assert handler.spans == [span]

    def test_collects_mixed_spans(self) -> None:
        handler = MemoryTraceHandler()
        obs = _make_observe_span()
        llm = _make_llm_span()
        asyncio.run(handler.on_observe(obs))
        asyncio.run(handler.on_llm(llm))
        assert handler.spans == [obs, llm]

    def test_get_trace_returns_tree_for_matching_trace_id(self) -> None:
        handler = MemoryTraceHandler()
        parent = _make_observe_span(span_id="p1", trace_id="t1")
        child = _make_llm_span(span_id="c1", trace_id="t1", parent_span_id="p1")
        asyncio.run(handler.on_observe(parent))
        asyncio.run(handler.on_llm(child))

        tree = handler.get_trace("t1")
        assert len(tree) == 1
        assert tree[0].span_id == "p1"
        assert len(tree[0].children) == 1
        assert tree[0].children[0].span_id == "c1"

    def test_get_trace_returns_empty_for_nonmatching_trace_id(self) -> None:
        handler = MemoryTraceHandler()
        asyncio.run(handler.on_observe(_make_observe_span(trace_id="t1")))
        assert handler.get_trace("t_nonexistent") == []

    def test_get_all_traces_groups_by_trace_id(self) -> None:
        handler = MemoryTraceHandler()
        asyncio.run(handler.on_observe(_make_observe_span(span_id="a1", trace_id="t1")))
        asyncio.run(handler.on_observe(_make_observe_span(span_id="b1", trace_id="t2")))
        asyncio.run(
            handler.on_llm(
                _make_llm_span(span_id="a2", trace_id="t1", parent_span_id="a1")
            )
        )

        traces = handler.get_all_traces()
        assert set(traces.keys()) == {"t1", "t2"}
        assert len(traces["t1"]) == 1  # one root
        assert len(traces["t1"][0].children) == 1
        assert len(traces["t2"]) == 1
        assert len(traces["t2"][0].children) == 0

    def test_clear_removes_all_spans(self) -> None:
        handler = MemoryTraceHandler()
        asyncio.run(handler.on_observe(_make_observe_span()))
        asyncio.run(handler.on_llm(_make_llm_span()))
        handler.clear()
        assert handler.spans == []


# ── capture_traces context manager tests ──────────────────────────────────


class TestCaptureTraces:
    """Tests for the capture_traces context manager."""

    def test_captures_spans_from_log(self) -> None:
        """Spans produced inside the context manager are captured."""
        with (
            capture_traces() as handler,
            px.start_observation(input="q", name="test") as observation,
        ):
            observation.set_output("a")
        assert len(handler.spans) == 1
        obs = handler.spans[0]
        assert isinstance(obs, ObserveSpan)
        assert obs.input == "q"
        assert obs.output == "a"

    def test_handler_accessible_after_context(self) -> None:
        with capture_traces() as handler, px.start_observation(input="q"):
            pass
        # Spans still accessible after exiting context
        assert len(handler.spans) == 1

    def test_spans_isolated_between_contexts(self) -> None:
        with capture_traces() as h1, px.start_observation(input="q1"):
            pass

        with capture_traces() as h2, px.start_observation(input="q2"):
            pass

        assert len(h1.spans) == 1
        obs1 = h1.spans[0]
        assert isinstance(obs1, ObserveSpan)
        assert obs1.input == "q1"
        assert len(h2.spans) == 1
        obs2 = h2.spans[0]
        assert isinstance(obs2, ObserveSpan)
        assert obs2.input == "q2"

    def test_handler_removed_after_context(self) -> None:
        """After exiting capture_traces, the handler no longer receives spans."""
        with capture_traces() as handler, px.start_observation(input="inside"):
            pass

        # Produce a span outside the context
        with px.start_observation(input="outside"):
            pass
        px.flush()

        # The handler should only have the span from inside
        assert len(handler.spans) == 1
        obs = handler.spans[0]
        assert isinstance(obs, ObserveSpan)
        assert obs.input == "inside"
