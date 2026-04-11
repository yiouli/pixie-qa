"""Factory for agent-deferred evaluators.

An agent evaluator is a concrete ``Evaluator`` implementation whose
``__call__`` raises :class:`AgentEvaluationPending` instead of returning
an :class:`~pixie.eval.evaluation.Evaluation`.  The test runner catches
this exception and records a :class:`~pixie.harness.run_result.PendingEvaluation`
in the entry result.

Usage::

    from pixie import create_agent_evaluator

    response_quality = create_agent_evaluator(
        name="ResponseQuality",
        criteria=(
            "The response directly addresses the user's question with "
            "accurate, well-structured information."
        ),
    )
"""

from __future__ import annotations

from pixie.eval.evaluable import Evaluable
from pixie.eval.evaluation import Evaluation


class AgentEvaluationPending(Exception):
    """Raised by agent evaluators to signal deferred grading.

    The test runner catches this and records a
    :class:`~pixie.harness.run_result.PendingEvaluation`.

    Attributes:
        evaluator_name: Display name for the evaluator.
        criteria: Grading instructions for the agent.
    """

    def __init__(self, evaluator_name: str, criteria: str) -> None:
        self.evaluator_name = evaluator_name
        self.criteria = criteria
        super().__init__(f"Agent evaluation pending: {evaluator_name}")


class _AgentEvaluator:
    """Evaluator that defers grading to a coding agent."""

    def __init__(self, name: str, criteria: str) -> None:
        self._name = name
        self._criteria = criteria

    @property
    def name(self) -> str:
        """Return the evaluator's display name."""
        return self._name

    async def __call__(self, evaluable: Evaluable) -> Evaluation:
        """Always raises :class:`AgentEvaluationPending`."""
        raise AgentEvaluationPending(self._name, self._criteria)


def create_agent_evaluator(
    name: str,
    criteria: str,
) -> _AgentEvaluator:
    """Create an evaluator whose grading is deferred to a coding agent.

    The returned evaluator satisfies the ``Evaluator`` protocol but
    always raises :class:`AgentEvaluationPending` when called.  The
    test runner catches this and records a pending evaluation.

    Args:
        name: Display name (shown in the scorecard).
        criteria: What to evaluate — the grading instructions the agent
            will follow when reviewing test results and traces.

    Returns:
        An evaluator callable that raises ``AgentEvaluationPending``.
    """
    return _AgentEvaluator(name=name, criteria=criteria)
