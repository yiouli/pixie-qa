"""Convenience functions that extract an ``Evaluable`` from a trace tree.

These are ``from_trace`` callables for use with :func:`~pixie.evals.eval_utils.run_and_evaluate`
and :func:`~pixie.evals.eval_utils.assert_pass`.
"""

from __future__ import annotations

from pixie.instrumentation.spans import LLMSpan
from pixie.storage.evaluable import Evaluable, as_evaluable
from pixie.storage.tree import ObservationNode


def _flatten(nodes: list[ObservationNode]) -> list[ObservationNode]:
    """Recursively flatten a tree of nodes into a flat list."""
    result: list[ObservationNode] = []
    for node in nodes:
        result.append(node)
        result.extend(_flatten(node.children))
    return result


def last_llm_call(trace: list[ObservationNode]) -> Evaluable:
    """Find the ``LLMSpan`` with the latest ``ended_at`` in the trace tree.

    Args:
        trace: The trace tree (list of root ``ObservationNode`` instances).

    Returns:
        An ``LLMSpanEval`` wrapping the most recently ended ``LLMSpan``.

    Raises:
        ValueError: If no ``LLMSpan`` exists in the trace.
    """
    all_nodes = _flatten(trace)
    llm_nodes = [n for n in all_nodes if isinstance(n.span, LLMSpan)]
    if not llm_nodes:
        raise ValueError("No LLMSpan found in the trace")
    llm_nodes.sort(key=lambda n: n.span.ended_at, reverse=True)
    return as_evaluable(llm_nodes[0].span)


def root(trace: list[ObservationNode]) -> Evaluable:
    """Return the first root node's span as ``Evaluable``.

    Args:
        trace: The trace tree (list of root ``ObservationNode`` instances).

    Returns:
        An ``Evaluable`` wrapping the first root node's span.

    Raises:
        ValueError: If the trace is empty.
    """
    if not trace:
        raise ValueError("Trace is empty")
    return as_evaluable(trace[0].span)
