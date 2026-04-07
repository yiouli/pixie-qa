Module pixie.eval.evaluation
============================
Evaluation primitives: Evaluation result, Evaluator protocol, evaluate().

Functions
---------

`evaluate(evaluator: Callable[..., Any], evaluable: Evaluable) ‑> pixie.eval.evaluation.Evaluation`
:   Run a single evaluator against a single evaluable.
    
    Behavior:
        1. If *evaluator* is sync, wrap via ``asyncio.to_thread``.
        2. Call evaluator with *evaluable*.
        3. Clamp returned ``score`` to [0.0, 1.0].
        4. If evaluator raises, the exception propagates to the caller.
           Evaluator errors (missing API keys, network failures, etc.)
           are never silently converted to a zero score.
    
    Args:
        evaluator: An evaluator callable (sync or async).
        evaluable: The data to evaluate.
    
    Raises:
        Exception: Any exception raised by the evaluator propagates
            unchanged so callers see clear, actionable errors.

Classes
-------

`Evaluation(score: float, reasoning: str, details: dict[str, Any] = <factory>)`
:   The result of a single evaluator applied to a single test case.
    
    Attributes:
        score: Evaluation score between 0.0 and 1.0.
        reasoning: Human-readable explanation (required).
        details: Arbitrary JSON-serializable metadata.

    ### Instance variables

    `details: dict[str, typing.Any]`
    :

    `reasoning: str`
    :

    `score: float`
    :

`Evaluator(*args, **kwargs)`
:   Protocol for evaluation callables.
    
    An evaluator is any callable (async or sync) matching this signature.
    Plain async functions, class instances with ``__call__``, or closures
    all satisfy this protocol. Sync evaluators are automatically wrapped
    via ``asyncio.to_thread`` at call time.

    ### Ancestors (in MRO)

    * typing.Protocol
    * typing.Generic