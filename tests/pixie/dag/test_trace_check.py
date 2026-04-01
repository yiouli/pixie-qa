"""Tests for pixie.dag.trace_check — trace-vs-DAG validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from pixie.dag import DagNode
from pixie.dag.trace_check import check_trace_against_dag
from pixie.instrumentation.spans import LLMSpan, ObserveSpan

# ── Helpers to build minimal trace trees ──────────────────────────


@dataclass
class FakeNode:
    """Minimal stand-in for ObservationNode used in tests."""

    span: ObserveSpan | LLMSpan
    children: list[FakeNode] = field(default_factory=list)

    @property
    def name(self) -> str:
        if isinstance(self.span, LLMSpan):
            return self.span.request_model
        return self.span.name or "(unnamed)"


_NOW = datetime.now(tz=timezone.utc)


def _observe_span(name: str) -> ObserveSpan:
    return ObserveSpan(
        span_id="s1",
        trace_id="t1",
        parent_span_id=None,
        started_at=_NOW,
        ended_at=_NOW,
        duration_ms=10.0,
        name=name,
        input=None,
        output=None,
        metadata={},
        error=None,
    )


def _llm_span(model: str = "gpt-4") -> LLMSpan:
    return LLMSpan(
        span_id="s2",
        trace_id="t1",
        parent_span_id="s1",
        started_at=_NOW,
        ended_at=_NOW,
        duration_ms=5.0,
        operation="chat",
        provider="openai",
        request_model=model,
        response_model=model,
        input_tokens=10,
        output_tokens=20,
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


# ── Tests ─────────────────────────────────────────────────────────


class TestCheckTraceAgainstDag:
    """Tests for check_trace_against_dag()."""

    def test_all_observable_nodes_matched(self) -> None:
        dag_nodes = [
            DagNode(
                id="root",
                name="handle_request",
                type="entry_point",
                code_pointer="app.py:handle",
                description="entry",
            ),
            DagNode(
                id="llm1",
                name="gpt-4",
                type="llm_call",
                code_pointer="app.py:llm",
                description="LLM",
                parent_id="root",
            ),
            DagNode(
                id="db",
                name="fetch_ctx",
                type="data_dependency",
                code_pointer="app.py:db",
                description="DB read",
                parent_id="root",
            ),
        ]
        trace = [
            FakeNode(
                span=_observe_span("handle_request"),
                children=[FakeNode(span=_llm_span("gpt-4"))],
            )
        ]
        result = check_trace_against_dag(dag_nodes, trace)
        assert result.valid
        assert "root" in result.matched
        assert "llm1" in result.matched
        # data_dependency is not observable — should not be in matched or unmatched
        assert "db" not in result.matched
        assert "db" not in result.unmatched

    def test_missing_observable_node_fails(self) -> None:
        dag_nodes = [
            DagNode(
                id="root",
                name="handle_request",
                type="entry_point",
                code_pointer="app.py:handle",
                description="entry",
            ),
            DagNode(
                id="obs1",
                name="process_data",
                type="observation",
                code_pointer="app.py:process",
                description="processing",
                parent_id="root",
            ),
        ]
        trace = [FakeNode(span=_observe_span("handle_request"))]
        result = check_trace_against_dag(dag_nodes, trace)
        assert not result.valid
        assert "obs1" in result.unmatched
        assert any("process_data" in e for e in result.errors)

    def test_extra_spans_reported(self) -> None:
        dag_nodes = [
            DagNode(
                id="root",
                name="handle_request",
                type="entry_point",
                code_pointer="app.py:handle",
                description="entry",
            ),
        ]
        trace = [
            FakeNode(
                span=_observe_span("handle_request"),
                children=[FakeNode(span=_llm_span("gpt-4"))],
            )
        ]
        result = check_trace_against_dag(dag_nodes, trace)
        assert result.valid  # extra spans don't cause failure
        assert "gpt-4" in result.extra_spans

    def test_non_observable_types_ignored(self) -> None:
        """data_dependency, intermediate_state, side_effect should not be checked."""
        dag_nodes = [
            DagNode(
                id="root",
                name="entry",
                type="entry_point",
                code_pointer="f.py:r",
                description="root",
            ),
            DagNode(
                id="dd",
                name="read_db",
                type="data_dependency",
                code_pointer="f.py:d",
                description="db",
                parent_id="root",
            ),
            DagNode(
                id="is",
                name="state",
                type="intermediate_state",
                code_pointer="f.py:s",
                description="state",
                parent_id="root",
            ),
            DagNode(
                id="se",
                name="write_log",
                type="side_effect",
                code_pointer="f.py:w",
                description="log",
                parent_id="root",
            ),
        ]
        trace = [FakeNode(span=_observe_span("entry"))]
        result = check_trace_against_dag(dag_nodes, trace)
        assert result.valid
        assert result.matched == ["root"]
        assert not result.unmatched

    def test_empty_dag_passes(self) -> None:
        trace = [FakeNode(span=_observe_span("something"))]
        result = check_trace_against_dag([], trace)
        assert result.valid
        assert "something" in result.extra_spans

    def test_empty_trace_with_observable_nodes_fails(self) -> None:
        dag_nodes = [
            DagNode(
                id="root",
                name="entry",
                type="entry_point",
                code_pointer="f.py:r",
                description="root",
            ),
        ]
        result = check_trace_against_dag(dag_nodes, [])
        assert not result.valid
        assert "root" in result.unmatched
