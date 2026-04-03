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

#: Default max number of runnables executing concurrently within a single
#: ``assert_pass`` / ``assert_dataset_pass`` call.  Override via
#: ``PIXIE_RUNNABLE_CONCURRENCY`` environment variable.
DEFAULT_RUNNABLE_CONCURRENCY: int = 4


def _run_sync_runnable_with_event_loop(
    runnable: Callable[..., Any],
    eval_input: Any,
) -> None:
    """Run a sync runnable in a worker thread with a thread-local event loop.

    Some sync wrappers call ``asyncio.get_event_loop().run_until_complete(...)``.
    Worker threads started by ``asyncio.to_thread`` do not have a current loop by
    default, so we provision one for compatibility and close it afterwards.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        maybe_awaitable = runnable(eval_input)
        if inspect.isawaitable(maybe_awaitable):
            loop.run_until_complete(maybe_awaitable)
    finally:
        asyncio.set_event_loop(None)
        loop.close()


class EvalAssertionError(AssertionError):
    """Raised by ``assert_pass`` when the pass criteria are not met.

    Carries the full results matrix for detailed failure reporting.
    """

    def __init__(
        self,
        message: str,
        results: list[list[Evaluation]],
    ) -> None:
        super().__init__(message)
        self.results = results


def _default_pass_criteria(
    results: list[list[Evaluation]],
) -> tuple[bool, str]:
    """Default pass criteria: every individual score must be >= 0.5."""
    all_scores = [e.score for input_ in results for e in input_]
    avg = sum(all_scores) / len(all_scores) if all_scores else 0.0
    passed = all(s >= 0.5 for s in all_scores)
    return (passed, f"Average score: {avg:.2f}, all >= 0.5: {passed}")


def _publish_to_scorecard(
    *,
    evaluators: list[Callable[..., Any]],
    eval_inputs: list[Any],
    results: list[list[Evaluation]],
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
                    else (
                        str(ev.expected_output)
                        if ev.expected_output is not None
                        else None
                    )
                ),
                "actual_output": (
                    str(ev.eval_output) if ev.eval_output is not None else None
                ),
                "metadata": ev.eval_metadata,
            }
            for ev in evaluables
        )
    else:
        ev_dicts = tuple(
            {
                "input": str(inp),
                "expected_output": None,
                "actual_output": None,
                "metadata": None,
            }
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


async def _run_and_capture(
    runnable: Callable[..., Any],
    eval_input: Any,
    *,
    expected_output: Any = _UNSET_SENTINEL,
    from_trace: Callable[[list[ObservationNode]], Evaluable] | None = None,
) -> tuple[Evaluable, list[ObservationNode]]:
    """Run *runnable(eval_input)* once, capture traces, return evaluable + tree.

    This is the single-execution helper used by both ``run_and_evaluate``
    and ``_process_single_input``.  The runnable is called exactly once;
    when multiple evaluators need the same output, callers should invoke
    this once and feed the returned evaluable to each evaluator.
    """
    with capture_traces() as handler:
        if inspect.iscoroutinefunction(runnable):
            await runnable(eval_input)
        else:
            await asyncio.to_thread(
                _run_sync_runnable_with_event_loop,
                runnable,
                eval_input,
            )

    if not handler.spans:
        raise ValueError("No spans captured during runnable execution")

    trace_tree = build_tree(handler.spans)

    if from_trace is not None:
        evaluable = from_trace(trace_tree)
    else:
        root_node = trace_tree[0]
        evaluable = as_evaluable(root_node.span)

    if expected_output is not _UNSET_SENTINEL:
        evaluable = Evaluable(
            eval_input=evaluable.eval_input,
            eval_output=evaluable.eval_output,
            eval_metadata=evaluable.eval_metadata,
            expected_output=expected_output,
        )

    return evaluable, trace_tree


async def run_and_evaluate(
    evaluator: Callable[..., Any],
    runnable: Callable[..., Any],
    eval_input: Any,
    *,
    expected_output: Any = _UNSET_SENTINEL,
    from_trace: Callable[[list[ObservationNode]], Evaluable] | None = None,
) -> Evaluation:
    """Run *runnable(eval_input)* while capturing traces, then evaluate.

    Convenience wrapper combining ``_run_and_capture`` and ``evaluate``.
    The runnable is called exactly once.

    Args:
        evaluator: An evaluator callable (sync or async).
        runnable: The application function to test.
        eval_input: The single input passed to *runnable*.
        expected_output: Optional expected value merged into the
            evaluable.
        from_trace: Optional callable to select a specific span from
            the trace tree for evaluation.

    Returns:
        The ``Evaluation`` result.

    Raises:
        ValueError: If no spans were captured during execution.
    """
    evaluable, trace_tree = await _run_and_capture(
        runnable,
        eval_input,
        expected_output=expected_output,
        from_trace=from_trace,
    )
    return await evaluate(evaluator, evaluable, trace=trace_tree)


def _get_runnable_concurrency() -> int:
    """Return the configured runnable concurrency limit."""
    import os

    raw = os.environ.get("PIXIE_RUNNABLE_CONCURRENCY")
    if raw is not None:
        return int(raw)
    return DEFAULT_RUNNABLE_CONCURRENCY


async def _process_single_input(
    idx: int,
    inp: Any,
    evaluators: list[Callable[..., Any]],
    evaluables: list[Evaluable] | None,
    runnable: Callable[..., Any],
    from_trace: Callable[[list[ObservationNode]], Evaluable] | None,
    semaphore: asyncio.Semaphore | None = None,
) -> list[Evaluation]:
    """Process a single dataset row: run runnable once, evaluate concurrently.

    The runnable is invoked at most once per input.  The resulting
    evaluable and trace tree are shared across all evaluators.

    When *semaphore* is provided the runnable execution is gated so that
    at most N runnables execute concurrently across all inputs.
    """

    async def _run_runnable() -> tuple[Evaluable, list[ObservationNode]]:
        """Run the runnable, respecting the concurrency semaphore."""
        kwargs: dict[str, Any] = {}
        if evaluables is not None:
            kwargs["expected_output"] = evaluables[idx].expected_output
        if from_trace is not None:
            kwargs["from_trace"] = from_trace

        if semaphore is not None:
            async with semaphore:
                return await _run_and_capture(runnable, inp, **kwargs)
        return await _run_and_capture(runnable, inp, **kwargs)

    if evaluables is not None:
        ev_item = evaluables[idx]
        if ev_item.eval_output is None:
            # Run the runnable ONCE, then feed the result to all evaluators
            evaluable, trace_tree = await _run_runnable()
            eval_coros = [
                evaluate(evaluator=ev, evaluable=evaluable, trace=trace_tree)
                for ev in evaluators
            ]
        else:
            eval_coros = [
                evaluate(evaluator=ev, evaluable=ev_item) for ev in evaluators
            ]
    else:
        # Run the runnable ONCE, then feed the result to all evaluators
        evaluable, trace_tree = await _run_runnable()
        eval_coros = [
            evaluate(evaluator=ev, evaluable=evaluable, trace=trace_tree)
            for ev in evaluators
        ]
    return list(await asyncio.gather(*eval_coros))


async def assert_pass(
    runnable: Callable[..., Any],
    eval_inputs: list[Any],
    evaluators: list[Callable[..., Any]],
    *,
    evaluables: list[Evaluable] | None = None,
    pass_criteria: (
        Callable[[list[list[Evaluation]]], tuple[bool, str]] | None
    ) = None,
    from_trace: Callable[[list[ObservationNode]], Evaluable] | None = None,
) -> None:
    """Run evaluators against a runnable over multiple inputs.

    For each input, runs the runnable once via ``_run_and_capture``,
    then evaluates with every evaluator concurrently via
    ``asyncio.gather``.

    The results matrix has shape ``[eval_inputs][evaluators]``.
    If the pass criteria are not met, raises :class:`EvalAssertionError`
    carrying the matrix.

    When ``evaluables`` is provided, behaviour depends on whether each
    item already has ``eval_output`` populated:

    - **eval_output is None** — the ``runnable`` is called via
      ``run_and_evaluate`` to produce an output from traces, and
      ``expected_output`` from the evaluable is merged into the result.
    - **eval_output is not None** — the evaluable is used directly
      (the runnable is not called for that item).

    Args:
        runnable: The application function to test.
        eval_inputs: List of inputs, each passed to *runnable*.
        evaluators: List of evaluator callables.
        evaluables: Optional list of ``Evaluable`` items, one per input.
            When provided, their ``expected_output`` is forwarded to
            ``run_and_evaluate``.  Must have the same length as
            *eval_inputs*.
        pass_criteria: Receives the results matrix, returns
            ``(passed, message)``.  Defaults to ``ScoreThreshold()``.
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
    sem = asyncio.Semaphore(_get_runnable_concurrency())

    input_tasks = [
        _process_single_input(
            idx, inp, evaluators, evaluables, runnable, from_trace, sem
        )
        for idx, inp in enumerate(eval_inputs)
    ]
    results: list[list[Evaluation]] = list(await asyncio.gather(*input_tasks))

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
    pass_criteria: (
        Callable[[list[list[Evaluation]]], tuple[bool, str]] | None
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
        pass_criteria: Receives the results matrix, returns
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
        pass_criteria=pass_criteria,
        from_trace=from_trace,
    )
