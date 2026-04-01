"""Validate a captured trace tree against a data-flow DAG."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pixie.dag import DagNode, parse_dag


@dataclass
class TraceCheckResult:
    """Result of checking a trace against the DAG."""

    valid: bool
    matched: list[str] = field(default_factory=list)  # DAG node IDs that matched
    unmatched: list[str] = field(
        default_factory=list
    )  # DAG node IDs not found in trace
    extra_spans: list[str] = field(default_factory=list)  # span names not in DAG
    errors: list[str] = field(default_factory=list)


def _collect_span_info(
    nodes: list[Any],
) -> list[dict[str, str]]:
    """Recursively collect span name and type info from a trace tree."""
    from pixie.instrumentation.spans import LLMSpan

    info: list[dict[str, str]] = []
    for node in nodes:
        span_type = "llm_call" if isinstance(node.span, LLMSpan) else "observation"
        info.append({"name": node.name, "type": span_type})
        info.extend(_collect_span_info(node.children))
    return info


def check_trace_against_dag(
    dag_nodes: list[DagNode],
    trace_tree: list[Any],
) -> TraceCheckResult:
    """Check that the trace tree contains spans matching the DAG's observable nodes.

    Only DAG nodes with type ``"llm_call"``, ``"observation"``, or ``"entry_point"``
    are expected to appear as spans. Other node types (data_dependency,
    intermediate_state, side_effect) are structural documentation and not
    expected to be separate spans.
    """
    result = TraceCheckResult(valid=True)

    # Types of DAG nodes that should appear as spans
    observable_types = {"llm_call", "observation", "entry_point"}

    # Collect observable DAG nodes
    observable_dag_nodes = [n for n in dag_nodes if n.type in observable_types]

    # Collect spans from trace
    span_info = _collect_span_info(trace_tree)
    span_names = {s["name"] for s in span_info}

    # Check each observable DAG node has a matching span
    for dag_node in observable_dag_nodes:
        if dag_node.name in span_names:
            result.matched.append(dag_node.id)
        else:
            result.unmatched.append(dag_node.id)

    # Find spans not accounted for by the DAG
    dag_names = {n.name for n in observable_dag_nodes}
    for span_name in span_names:
        if span_name not in dag_names:
            result.extra_spans.append(span_name)

    if result.unmatched:
        result.valid = False
        for node_id in result.unmatched:
            node = next(n for n in dag_nodes if n.id == node_id)
            result.errors.append(
                f"DAG node '{node.id}' (name='{node.name}', type={node.type}) "
                f"has no matching span in the trace."
            )

    return result


async def check_last_trace(
    dag_json_path: Path,
) -> TraceCheckResult:
    """Load the most recent trace and check it against a DAG JSON file.

    Returns a TraceCheckResult with match details.
    """
    from piccolo.engine.sqlite import SQLiteEngine

    from pixie.config import get_config
    from pixie.storage.store import ObservationStore

    # Parse DAG
    dag_nodes, parse_errors = parse_dag(dag_json_path)
    if parse_errors:
        return TraceCheckResult(valid=False, errors=parse_errors)

    # Load latest trace
    config = get_config()
    engine = SQLiteEngine(path=config.db_path)
    store = ObservationStore(engine=engine)

    traces = await store.list_traces(limit=1)
    if not traces:
        return TraceCheckResult(
            valid=False,
            errors=["No traces found. Run the app first to produce a trace."],
        )

    trace_id = traces[0]["trace_id"]
    tree = await store.get_trace(trace_id)
    if not tree:
        return TraceCheckResult(
            valid=False,
            errors=[f"No spans found for trace '{trace_id}'."],
        )

    return check_trace_against_dag(dag_nodes, tree)
