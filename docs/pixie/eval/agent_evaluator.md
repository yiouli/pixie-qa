Module pixie.eval.agent_evaluator
=================================
Factory for agent-deferred evaluators.

An agent evaluator is a concrete ``Evaluator`` implementation whose
``__call__`` raises :class:`AgentEvaluationPending` instead of returning
an :class:`~pixie.eval.evaluation.Evaluation`.  The evaluation harness catches
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

Functions
---------

`def create_agent_evaluator(name: str, criteria: str) ‑> pixie.eval.agent_evaluator._AgentEvaluator`
:   Create an evaluator whose grading is deferred to a coding agent.
    
    The returned evaluator satisfies the ``Evaluator`` protocol but
    always raises :class:`AgentEvaluationPending` when called.  The
    evaluation harness catches this and records a pending evaluation.
    
    Args:
        name: Display name (shown in the scorecard).
        criteria: What to evaluate — the grading instructions the agent
            will follow when reviewing test results and traces.
    
    Returns:
        An evaluator callable that raises ``AgentEvaluationPending``.

Classes
-------

`AgentEvaluationPending(evaluator_name: str, criteria: str)`
:   Raised by agent evaluators to signal deferred grading.
    
    The evaluation harness catches this and records a
    :class:`~pixie.harness.run_result.PendingEvaluation`.
    
    Attributes:
        evaluator_name: Display name for the evaluator.
        criteria: Grading instructions for the agent.

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException