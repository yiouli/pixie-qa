"""Higher-level eval utilities: run_and_evaluate, assert_pass, assert_dataset_pass."""

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

# Private sentinel — distinguishes "caller did not pass expected_output" from None.
_UNSET_SENTINEL: Any = object()


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


def _publish_to_scorecard(
    *,
    evaluators: list[Callable[..., Any]],
    eval_inputs: list[Any],
    results: list[list[list[Evaluation]]],
    passed: bool,
    criteria_message: str,
    criteria: object,
    evaluables: list[Evaluable] | None = None,
) -> None:
    """Push an :class:`AssertRecord` to the active scorecard collector.

    This is a no-op when no collector is active (i.e. when tests are
    not run via ``pixie test``).
    """
    from pixie.evals.scorecard import (
        AssertRecord,
        _describe_criteria,
        _evaluator_display_name,
        _input_label,
        get_active_collector,
    )
    from pixie.storage.evaluable import _Unset

    collector = get_active_collector()
    if collector is None:
        return

    evaluator_names = tuple(_evaluator_display_name(ev) for ev in evaluators)
    input_labels = tuple(_input_label(inp) for inp in eval_inputs)

    # Build per-row context for the scorecard detail modal
    if evaluables is not None:
        ev_dicts: tuple[dict[str, Any], ...] = tuple(
            {
                "input": str(ev.eval_input) if ev.eval_input is not None else None,
                "expected_output": (
                    None
                    if isinstance(ev.expected_output, _Unset)
                    else (str(ev.expected_output) if ev.expected_output is not None else None)
                ),
                "actual_output": str(ev.eval_output) if ev.eval_output is not None else None,
                "metadata": ev.eval_metadata,
            }
            for ev in evaluables
        )
    else:
        ev_dicts = tuple(
            {"input": str(inp), "expected_output": None, "actual_output": None, "metadata": None}
            for inp in eval_inputs
        )

    record = AssertRecord(
        evaluator_names=evaluator_names,
        input_labels=input_labels,
        results=results,
        passed=passed,
        criteria_message=criteria_message,
        scoring_strategy=_describe_criteria(criteria),
        evaluable_dicts=ev_dicts,
    )
    collector.record(record)


async def run_and_evaluate(
    evaluator: Callable[..., Any],
    runnable: Callable[..., Any],
    eval_input: Any,
    *,
    expected_output: Any = _UNSET_SENTINEL,
    from_trace: Callable[[list[ObservationNode]], Evaluable] | None = None,
) -> Evaluation:
    """Run *runnable(eval_input)* while capturing traces, then evaluate.

    1. Initialises instrumentation (no-op if already done) and registers
       an in-memory trace handler scoped to this call.
    2. Calls ``runnable(eval_input)`` — async runnables are awaited, sync
       ones are run via ``asyncio.to_thread``.
    3. Flushes the delivery queue so all spans reach the handler.
    4. Builds the trace tree and determines the evaluable:

       - If *from_trace* is provided, ``from_trace(tree)`` selects the
         span to evaluate.
       - Otherwise the root observation span is used.

    5. If *expected_output* is provided, merges it into the evaluable
       (span-derived evaluables never carry expected values).
    6. Runs the evaluator and returns the ``Evaluation``.

    Args:
        evaluator: An evaluator callable (sync or async).
        runnable: The application function to test.
        eval_input: The single input passed to *runnable*.
        expected_output: Optional expected value merged into the
            evaluable.  Span-derived evaluables always have
            ``expected_output=UNSET``; this parameter lets callers
            inject the reference value.
        from_trace: Optional callable to select a specific span from
            the trace tree for evaluation.

    Returns:
        The ``Evaluation`` result.

    Raises:
        ValueError: If no spans were captured during execution.
    """
    with capture_traces() as handler:
        if inspect.iscoroutinefunction(runnable):
            await runnable(eval_input)
        else:
            await asyncio.to_thread(runnable, eval_input)

    # capture_traces flushes on exit, so handler.spans is populated
    if not handler.spans:
        raise ValueError("No spans captured during runnable execution")

    trace_tree = build_tree(handler.spans)

    if from_trace is not None:
        evaluable = from_trace(trace_tree)
    else:
        root_node = trace_tree[0]
        evaluable = as_evaluable(root_node.span)

    # Merge expected_output into the span-derived evaluable when provided
    if expected_output is not _UNSET_SENTINEL:
        evaluable = Evaluable(
            eval_input=evaluable.eval_input,
            eval_output=evaluable.eval_output,
            eval_metadata=evaluable.eval_metadata,
            expected_output=expected_output,
        )

    return await evaluate(evaluator, evaluable, trace=trace_tree)


async def assert_pass(
    runnable: Callable[..., Any],
    eval_inputs: list[Any],
    evaluators: list[Callable[..., Any]],
    *,
    evaluables: list[Evaluable] | None = None,
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

    The full results tensor has shape ``[passes][eval_inputs][evaluators]``.
    If the pass criteria are not met, raises :class:`EvalAssertionError`
    carrying the tensor.

    When ``evaluables`` is provided, each item is used directly as the
    evaluable for the corresponding input (it already carries its own
    ``expected_output``).  When ``evaluables`` is ``None``, the evaluable
    is constructed from the captured trace as before.

    Args:
        runnable: The application function to test.
        eval_inputs: List of inputs, each passed to *runnable*.
        evaluators: List of evaluator callables.
        evaluables: Optional list of ``Evaluable`` items, one per input.
            Must have the same length as *eval_inputs* when provided.
        passes: How many times to run the entire test matrix.
        pass_criteria: Receives the results tensor, returns
            ``(passed, message)``.  Defaults to "every score >= 0.5".
        from_trace: Optional span selector forwarded to
            ``run_and_evaluate``.

    Raises:
        EvalAssertionError: When pass criteria are not met.
        ValueError: When *evaluables* length does not match *eval_inputs*.
    """
    if evaluables is not None and len(evaluables) != len(eval_inputs):
        raise ValueError(
            f"evaluables length ({len(evaluables)}) "
            f"must match eval_inputs length ({len(eval_inputs)})"
        )

    criteria = pass_criteria or ScoreThreshold()
    results: list[list[list[Evaluation]]] = []

    for _ in range(passes):
        pass_results: list[list[Evaluation]] = []
        for idx, inp in enumerate(eval_inputs):
            if evaluables is not None:
                # Use provided evaluable directly — skip trace capture
                ev_item = evaluables[idx]
                eval_coros = [
                    evaluate(evaluator=ev, evaluable=ev_item) for ev in evaluators
                ]
            else:
                eval_coros = [
                    run_and_evaluate(
                        evaluator=ev,
                        runnable=runnable,
                        eval_input=inp,
                        from_trace=from_trace,
                    )
                    for ev in evaluators
                ]
            input_evals = list(await asyncio.gather(*eval_coros))
            pass_results.append(input_evals)
        results.append(pass_results)

    passed, message = criteria(results)

    # ── Publish to scorecard collector (if active) ─────────────────
    _publish_to_scorecard(
        evaluators=evaluators,
        eval_inputs=eval_inputs,
        results=results,
        passed=passed,
        criteria_message=message,
        criteria=criteria,
        evaluables=evaluables,
    )

    if not passed:
        raise EvalAssertionError(message, results=results)


async def assert_dataset_pass(
    runnable: Callable[..., Any],
    dataset_name: str,
    evaluators: list[Callable[..., Any]],
    *,
    dataset_dir: str | None = None,
    passes: int = 1,
    pass_criteria: (
        Callable[[list[list[list[Evaluation]]]], tuple[bool, str]] | None
    ) = None,
    from_trace: Callable[[list[ObservationNode]], Evaluable] | None = None,
) -> None:
    """Load a dataset by name, then run ``assert_pass`` with its items.

    This is a convenience wrapper that:

    1. Loads the dataset from the ``DatasetStore``.
    2. Extracts ``eval_input`` from each item as the runnable inputs.
    3. Uses the full ``Evaluable`` items (which carry ``expected_output``)
       as the evaluables.
    4. Delegates to ``assert_pass``.

    Args:
        runnable: The application function to test.
        dataset_name: Name of the dataset to load.
        evaluators: List of evaluator callables.
        dataset_dir: Override directory for the dataset store.
            When ``None``, reads from ``PixieConfig.dataset_dir``.
        passes: How many times to run the entire test matrix.
        pass_criteria: Receives the results tensor, returns
            ``(passed, message)``.
        from_trace: Optional span selector forwarded to
            ``assert_pass``.

    Raises:
        FileNotFoundError: If no dataset with *dataset_name* exists.
        EvalAssertionError: When pass criteria are not met.
    """
    from pixie.dataset.store import DatasetStore

    store = DatasetStore(dataset_dir=dataset_dir)
    dataset = store.get(dataset_name)
    items = list(dataset.items)
    eval_inputs = [item.eval_input for item in items]

    await assert_pass(
        runnable=runnable,
        eval_inputs=eval_inputs,
        evaluators=evaluators,
        evaluables=items,
        passes=passes,
        pass_criteria=pass_criteria,
        from_trace=from_trace,
    )
