"""Tests for pixie.instrumentation.context — _SpanContext."""

from __future__ import annotations

import pytest

import pixie.instrumentation as px
from pixie.instrumentation.spans import ObserveSpan

from .conftest import RecordingHandler


class TestSpanContextSetters:
    """Tests for set_output() and set_metadata()."""

    def test_set_output(self, recording_handler: RecordingHandler) -> None:
        px.init()
        px.add_handler(recording_handler)
        with px.log(input="q") as span:
            span.set_output("answer")
        px.flush()
        assert len(recording_handler.observe_spans) == 1
        assert recording_handler.observe_spans[0].output == "answer"

    def test_set_metadata(self, recording_handler: RecordingHandler) -> None:
        px.init()
        px.add_handler(recording_handler)
        with px.log() as span:
            span.set_metadata("k1", "v1")
            span.set_metadata("k2", 42)
        px.flush()
        obs = recording_handler.observe_spans[0]
        assert obs.metadata == {"k1": "v1", "k2": 42}


class TestSpanContextSnapshot:
    """Tests for _snapshot() producing correct frozen ObserveSpan."""

    def test_snapshot_produces_observe_span(
        self, recording_handler: RecordingHandler
    ) -> None:
        px.init()
        px.add_handler(recording_handler)
        with px.log(input="hello", name="test_block") as span:
            span.set_output("world")
        px.flush()

        obs = recording_handler.observe_spans[0]
        assert isinstance(obs, ObserveSpan)
        assert obs.input == "hello"
        assert obs.output == "world"
        assert obs.name == "test_block"
        assert obs.error is None
        assert len(obs.span_id) == 16
        assert len(obs.trace_id) == 32

    def test_snapshot_with_default_name(
        self, recording_handler: RecordingHandler
    ) -> None:
        px.init()
        px.add_handler(recording_handler)
        with px.log():
            pass
        px.flush()
        obs = recording_handler.observe_spans[0]
        assert obs.name == "observe"

    def test_snapshot_timing(self, recording_handler: RecordingHandler) -> None:
        px.init()
        px.add_handler(recording_handler)
        with px.log():
            pass
        px.flush()
        obs = recording_handler.observe_spans[0]
        assert obs.started_at is not None
        assert obs.ended_at is not None
        assert obs.duration_ms >= 0


class TestSpanContextError:
    """Tests for exception handling inside log() blocks."""

    def test_exception_sets_error_field(
        self, recording_handler: RecordingHandler
    ) -> None:
        px.init()
        px.add_handler(recording_handler)
        with pytest.raises(ValueError, match="test error"), px.log(input="q"):
            raise ValueError("test error")
        px.flush()
        obs = recording_handler.observe_spans[0]
        assert obs.error == "ValueError"

    def test_exception_is_reraised(self, recording_handler: RecordingHandler) -> None:
        px.init()
        px.add_handler(recording_handler)
        with pytest.raises(RuntimeError), px.log():
            raise RuntimeError("boom")


class TestSpanContextNesting:
    """Tests for nesting log() blocks."""

    def test_nested_parent_span_id(self, recording_handler: RecordingHandler) -> None:
        px.init()
        px.add_handler(recording_handler)
        with px.log(name="outer"):  # noqa: SIM117
            with px.log(name="inner"):
                pass
        px.flush()

        assert len(recording_handler.observe_spans) == 2
        # Inner is submitted first (innermost finally runs first)
        inner_obs = recording_handler.observe_spans[0]
        outer_obs = recording_handler.observe_spans[1]
        assert inner_obs.name == "inner"
        assert outer_obs.name == "outer"
        # Inner's parent should be outer's span_id
        assert inner_obs.parent_span_id == outer_obs.span_id
        # They share the same trace_id
        assert inner_obs.trace_id == outer_obs.trace_id
