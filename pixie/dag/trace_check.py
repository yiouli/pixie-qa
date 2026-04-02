"""Validate a captured trace tree against a data-flow DAG."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pixie.dag import DagNode, is_valid_dag_name, parse_dag


@dataclass
class TraceCheckResult:
    """Result of checking a trace against the DAG."""

    valid: bool
    matched: list[str] = field(default_factory=list)  # DAG node names that matched
    unmatched: list[str] = field(
        default_factory=list
    )  # DAG node names not found in trace
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
    """Check that the trace tree contains spans matching the DAG nodes.

    Matching rules:

    - If ``is_llm_call`` is ``true`` on a DAG node, the check passes when at
      least one LLM span exists in the trace. Name matching is skipped.
    - Otherwise, the DAG node name must match a non-LLM span name exactly.
    """
    result = TraceCheckResult(valid=True)
    unmatched_reasons: dict[str, str] = {}

    # Enforce naming contract even when callers skip explicit DAG validation.
    invalid_names: list[str] = []
    for node in dag_nodes:
        if not is_valid_dag_name(node.name):
            invalid_names.append(
                f"DAG node '{node.name}': name must be lower_snake_case "
                "(e.g., 'handle_turn')."
            )
        if node.parent is not None and not is_valid_dag_name(node.parent):
            invalid_names.append(
                f"DAG node '{node.name}': parent '{node.parent}' must be "
                "lower_snake_case."
            )
    if invalid_names:
        return TraceCheckResult(valid=False, errors=invalid_names)

    # Collect spans from trace
    span_info = _collect_span_info(trace_tree)
    span_names_by_type: dict[str, set[str]] = {"observation": set(), "llm_call": set()}
    for span in span_info:
        span_names_by_type.setdefault(span["type"], set()).add(span["name"])

    span_names = span_names_by_type["observation"] | span_names_by_type["llm_call"]
    has_llm_spans = any(s["type"] == "llm_call" for s in span_info)
    has_llm_dag_nodes = any(node.is_llm_call for node in dag_nodes)

    # Check each DAG node has a matching span according to its llm flag.
    matched_span_names: set[str] = set()
    for dag_node in dag_nodes:
        if dag_node.is_llm_call:
            if has_llm_spans:
                result.matched.append(dag_node.name)
            else:
                result.unmatched.append(dag_node.name)
                unmatched_reasons[dag_node.name] = "missing_llm_span"
            continue

        if dag_node.name not in span_names:
            result.unmatched.append(dag_node.name)
            unmatched_reasons[dag_node.name] = "missing_named_span"
            continue

        # For non-LLM DAG nodes, ensure the matched span is non-LLM.
        if (
            dag_node.name in span_names_by_type["llm_call"]
            and dag_node.name not in span_names_by_type["observation"]
        ):
            result.unmatched.append(dag_node.name)
            unmatched_reasons[dag_node.name] = "llm_flag_mismatch"
        else:
            result.matched.append(dag_node.name)
            matched_span_names.add(dag_node.name)

    # Find spans not accounted for by the DAG
    for span_name in sorted(span_names_by_type["observation"]):
        if span_name not in matched_span_names:
            result.extra_spans.append(span_name)
    if not has_llm_dag_nodes:
        for span_name in sorted(span_names_by_type["llm_call"]):
            result.extra_spans.append(span_name)

    if result.unmatched:
        result.valid = False
        for node_name in result.unmatched:
            node = next(n for n in dag_nodes if n.name == node_name)
            reason = unmatched_reasons.get(node_name)
            if reason == "missing_llm_span":
                result.errors.append(
                    f"DAG node '{node.name}' (is_llm_call=true) expects at least "
                    f"one LLM span in the trace, but none were found. "
                    f"Common fix: ensure `enable_storage()` is called BEFORE the "
                    f"LLM client (OpenAI, Anthropic, etc.) is created."
                )
            elif reason == "llm_flag_mismatch":
                result.errors.append(
                    f"DAG node '{node.name}' has is_llm_call=false but matched an LLM "
                    "span. Fix: set `is_llm_call: true` on this node in the DAG JSON."
                )
            else:
                result.errors.append(
                    f"DAG node '{node.name}' has no matching span in the trace. "
                    f"This means either: (1) the function at `code_pointer` is not "
                    f"decorated with `@observe(name='{node.name}')`, or (2) the "
                    f"function was not called during the trace run. Fix: add "
                    f"`@observe(name='{node.name}')` to the function specified by "
                    f"the node's `code_pointer`, or if already decorated, ensure "
                    f"the name matches exactly."
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
