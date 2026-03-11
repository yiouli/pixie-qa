"""Tests for pixie.evals.trace_helpers — last_llm_call, root."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from pixie.evals.trace_helpers import last_llm_call, root
from pixie.instrumentation.spans import LLMSpan, ObserveSpan
from pixie.storage.evaluable import LLMSpanEval, ObserveSpanEval
from pixie.storage.tree import ObservationNode


def _make_observe_span(
    name: str = "test",
    span_id: str = "0000000000000001",
    parent_span_id: str | None = None,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
) -> ObserveSpan:
    now = started_at or datetime.now(tz=timezone.utc)
    end = ended_at or now
    return ObserveSpan(
        span_id=span_id,
        trace_id="00000000000000000000000000000001",
        parent_span_id=parent_span_id,
        started_at=now,
        ended_at=end,
        duration_ms=0.0,
        name=name,
        input="hello",
        output="world",
        metadata={},
        error=None,
    )


def _make_llm_span(
    span_id: str = "0000000000000002",
    parent_span_id: str | None = None,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
    request_model: str = "gpt-4",
) -> LLMSpan:
    now = started_at or datetime.now(tz=timezone.utc)
    end = ended_at or now
    return LLMSpan(
        span_id=span_id,
        trace_id="00000000000000000000000000000001",
        parent_span_id=parent_span_id,
        started_at=now,
        ended_at=end,
        duration_ms=0.0,
        operation="chat",
        provider="openai",
        request_model=request_model,
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


class TestLastLlmCall:
    """Tests for the last_llm_call trace helper."""

    def test_returns_llm_span_with_latest_ended_at(self) -> None:
        t1 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        t2 = t1 + timedelta(seconds=1)
        t3 = t1 + timedelta(seconds=2)

        early = _make_llm_span(span_id="a1", ended_at=t1, request_model="early")
        late = _make_llm_span(span_id="a2", ended_at=t3, request_model="late")
        mid = _make_llm_span(span_id="a3", ended_at=t2, request_model="mid")

        trace = [
            ObservationNode(span=early),
            ObservationNode(span=mid),
            ObservationNode(span=late),
        ]

        result = last_llm_call(trace)
        assert isinstance(result, LLMSpanEval)
        assert result.eval_metadata["request_model"] == "late"

    def test_raises_value_error_when_no_llm_span(self) -> None:
        obs = _make_observe_span()
        trace = [ObservationNode(span=obs)]

        with pytest.raises(ValueError, match="No LLMSpan found"):
            last_llm_call(trace)

    def test_works_with_multi_level_nested_traces(self) -> None:
        t1 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        t2 = t1 + timedelta(seconds=5)

        obs = _make_observe_span(span_id="root")
        llm_early = _make_llm_span(span_id="llm1", parent_span_id="root", ended_at=t1)
        inner_obs = _make_observe_span(
            name="inner", span_id="inner", parent_span_id="root"
        )
        llm_late = _make_llm_span(
            span_id="llm2", parent_span_id="inner", ended_at=t2, request_model="nested"
        )

        # Build nested tree: root -> [llm_early, inner_obs -> [llm_late]]
        inner_node = ObservationNode(
            span=inner_obs, children=[ObservationNode(span=llm_late)]
        )
        root_node = ObservationNode(
            span=obs, children=[ObservationNode(span=llm_early), inner_node]
        )
        trace = [root_node]

        result = last_llm_call(trace)
        assert isinstance(result, LLMSpanEval)
        assert result.eval_metadata["request_model"] == "nested"

    def test_raises_on_empty_trace(self) -> None:
        with pytest.raises(ValueError, match="No LLMSpan found"):
            last_llm_call([])


class TestRoot:
    """Tests for the root trace helper."""

    def test_returns_first_root_node_as_evaluable(self) -> None:
        obs = _make_observe_span(name="my-root")
        trace = [ObservationNode(span=obs)]

        result = root(trace)
        assert isinstance(result, ObserveSpanEval)
        assert result.eval_input == "hello"

    def test_returns_llm_span_evaluable_when_root_is_llm(self) -> None:
        llm = _make_llm_span()
        trace = [ObservationNode(span=llm)]

        result = root(trace)
        assert isinstance(result, LLMSpanEval)

    def test_raises_value_error_on_empty_trace(self) -> None:
        with pytest.raises(ValueError, match="Trace is empty"):
            root([])
