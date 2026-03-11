"""Higher-level eval utilities: run_and_evaluate, assert_pass, EvalAssertionError."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import Any

from pixie.evals.criteria import ScoreThreshold
from pixie.evals.evaluation import Evaluation, evaluate
from pixie.evals.trace_capture import capture_traces
from pixie.storage.evaluable import Evaluable, as_evaluable
from pixie.storage.tree import ObservationNode, build_tree


class EvalAssertionError(AssertionError):
    """Raised by ``assert_pass`` when the pass criteria are not met.

    Carries the full results tensor for detailed failure reporting.
    """

    def __init__(
        self,
        message: str,
        results: list[list[list[Evaluation]]],
    ) -> None:
        super().__init__(message)
        self.results = results


def _default_pass_criteria(
    results: list[list[list[Evaluation]]],
) -> tuple[bool, str]:
    """Default pass criteria: every individual score must be >= 0.5."""
    all_scores = [e.score for pass_ in results for input_ in pass_ for e in input_]
    avg = sum(all_scores) / len(all_scores) if all_scores else 0.0
    passed = all(s >= 0.5 for s in all_scores)
    return (passed, f"Average score: {avg:.2f}, all >= 0.5: {passed}")


async def run_and_evaluate(
    evaluator: Callable[..., Any],
    runnable: Callable[..., Any],
    input: Any,  # noqa: A002
    *,
    from_trace: Callable[[list[ObservationNode]], Evaluable] | None = None,
) -> Evaluation:
    """Run *runnable(input)* while capturing traces, then evaluate.

    1. Initialises instrumentation (no-op if already done) and registers
       an in-memory trace handler scoped to this call.
    2. Calls ``runnable(input)`` — async runnables are awaited, sync ones
       are run via ``asyncio.to_thread``.
    3. Flushes the delivery queue so all spans reach the handler.
    4. Builds the trace tree and determines the evaluable:

       - If *from_trace* is provided, ``from_trace(tree)`` selects the
         span to evaluate.
       - Otherwise the root observation span is used.

    5. Runs the evaluator and returns the ``Evaluation``.

    Args:
        evaluator: An evaluator callable (sync or async).
        runnable: The application function to test.
        input: The single input passed to *runnable*.
        from_trace: Optional callable to select a specific span from
            the trace tree for evaluation.

    Returns:
        The ``Evaluation`` result.

    Raises:
        ValueError: If no spans were captured during execution.
    """
    with capture_traces() as handler:
        if inspect.iscoroutinefunction(runnable):
            await runnable(input)
        else:
            await asyncio.to_thread(runnable, input)

    # capture_traces flushes on exit, so handler.spans is populated
    if not handler.spans:
        raise ValueError("No spans captured during runnable execution")

    trace_tree = build_tree(handler.spans)

    if from_trace is not None:
        evaluable = from_trace(trace_tree)
    else:
        root_node = trace_tree[0]
        evaluable = as_evaluable(root_node.span)

    return await evaluate(evaluator, evaluable, trace=trace_tree)


async def assert_pass(
    runnable: Callable[..., Any],
    inputs: list[Any],
    evaluators: list[Callable[..., Any]],
    *,
    passes: int = 1,
    pass_criteria: (
        Callable[[list[list[list[Evaluation]]]], tuple[bool, str]] | None
    ) = None,
    from_trace: Callable[[list[ObservationNode]], Evaluable] | None = None,
) -> None:
    """Run evaluators against a runnable over multiple inputs and passes.

    For each pass and each input, calls ``run_and_evaluate`` for every
    evaluator.  Evaluators for a single input are run concurrently via
    ``asyncio.gather``.  Inputs within a pass are run sequentially.

    The full results tensor has shape ``[passes][inputs][evaluators]``.
    If the pass criteria are not met, raises :class:`EvalAssertionError`
    carrying the tensor.

    Args:
        runnable: The application function to test.
        inputs: List of inputs, each passed to *runnable*.
        evaluators: List of evaluator callables.
        passes: How many times to run the entire test matrix.
        pass_criteria: Receives the results tensor, returns
            ``(passed, message)``.  Defaults to "every score >= 0.5".
        from_trace: Optional span selector forwarded to
            ``run_and_evaluate``.

    Raises:
        EvalAssertionError: When pass criteria are not met.
    """
    criteria = pass_criteria or ScoreThreshold()
    results: list[list[list[Evaluation]]] = []

    for _ in range(passes):
        pass_results: list[list[Evaluation]] = []
        for inp in inputs:
            eval_coros = [
                run_and_evaluate(
                    evaluator=ev,
                    runnable=runnable,
                    input=inp,
                    from_trace=from_trace,
                )
                for ev in evaluators
            ]
            input_evals = list(await asyncio.gather(*eval_coros))
            pass_results.append(input_evals)
        results.append(pass_results)

    passed, message = criteria(results)
    if not passed:
        raise EvalAssertionError(message, results=results)
