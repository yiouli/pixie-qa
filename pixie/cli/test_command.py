"""``pixie test`` CLI entry point.

Usage::

    pixie test [path] [--verbose] [--no-open]

Supports two modes:

1. **Dataset mode** — when *path* is a ``.json`` file or a directory
   containing dataset JSON files. Each dataset produces its own result.
2. **Default** — no path searches the pixie datasets directory.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pixie.instrumentation as px
from pixie.evals.dataset_runner import (
    _resolve_evaluator,
    _resolve_runnable,
    _short_name,
    discover_dataset_files,
    load_dataset_entries,
)
from pixie.evals.eval_utils import _get_runnable_concurrency
from pixie.evals.evaluation import Evaluation, evaluate
from pixie.evals.rate_limiter import configure_rate_limits_from_config
from pixie.evals.test_result import (
    DatasetResult,
    EntryResult,
    EvaluationResult,
    RunResult,
    generate_test_id,
    save_test_result,
)
from pixie.instrumentation.wrap import WrapRegistryMissError, WrapTypeMismatchError
from pixie.instrumentation.wrap_registry import (
    clear_capture_registry,
    clear_input_registry,
    get_capture_registry,
    init_capture_registry,
    set_input_registry,
)
from pixie.storage.evaluable import Evaluable, _Unset


def _get_dependency_input(evaluable: Evaluable) -> dict[str, str] | None:
    """Extract dependency_input from evaluable metadata, if present."""
    if evaluable.eval_metadata is None:
        return None
    raw = evaluable.eval_metadata.get("dependency_input")
    if isinstance(raw, dict):
        return {k: v for k, v in raw.items() if isinstance(v, str)}
    return None


async def _run_entry_new_mode(
    evaluable: Evaluable,
    evaluator_names: list[str],
    runnable: Callable[..., Any],
    semaphore: asyncio.Semaphore,
    dependency_input: dict[str, str],
) -> EntryResult:
    """Process a single dataset entry in new (wrap-registry) mode.

    Sets up the input/capture registries and calls the runnable with
    entry_input only.  ``wrap()`` handles input injection and output/state
    capture through the registries.  ``PIXIE_TRACING`` is effectively
    disabled for eval runs because the registry takes precedence — the
    tracing path in ``wrap()`` is only reached when no registry is active.
    """
    async with semaphore:
        init_capture_registry()
        set_input_registry(dependency_input)

        entry_input = evaluable.eval_input
        try:
            if inspect.iscoroutinefunction(runnable):
                await runnable(entry_input)
            else:
                runnable(entry_input)
        except (WrapRegistryMissError, WrapTypeMismatchError) as exc:
            clear_input_registry()
            clear_capture_registry()
            # Report per-entry errors without aborting the whole run
            return EntryResult(
                input=entry_input,
                output=None,
                expected_output=None,
                description=evaluable.description,
                evaluations=[
                    EvaluationResult(
                        evaluator="WrapError",
                        score=0.0,
                        reasoning=str(exc),
                    )
                ],
            )

        captures = dict(get_capture_registry() or {})
        clear_input_registry()
        clear_capture_registry()

    # Build evaluable from captures
    captured_output = captures if captures else {}
    primary_output: Any = next(iter(captured_output.values()), None) if captured_output else None

    updated = evaluable.model_copy(
        update={
            "eval_output": primary_output,
            "captured_output": captured_output or None,
        }
    )

    evaluators = [_resolve_evaluator(name) for name in evaluator_names]
    short_names = [_short_name(n) for n in evaluator_names]

    evals: list[Evaluation] = list(
        await asyncio.gather(*(evaluate(ev, updated) for ev in evaluators))
    )

    exp_out = updated.expected_output
    expected_output = (
        None if isinstance(exp_out, _Unset) or exp_out is None else exp_out
    )

    eval_results = [
        EvaluationResult(
            evaluator=name,
            score=ev.score,
            reasoning=ev.reasoning,
        )
        for name, ev in zip(short_names, evals, strict=True)
    ]

    return EntryResult(
        input=updated.eval_input,
        output=updated.eval_output,
        expected_output=expected_output,
        description=updated.description,
        evaluations=eval_results,
    )


async def _run_entry(
    evaluable: Evaluable,
    evaluator_names: list[str],
    runnable: Callable[..., Any],
    semaphore: asyncio.Semaphore,
) -> EntryResult:
    """Process a single dataset entry: call runnable, then evaluate concurrently.

    Dispatches to new-mode (registry-based) or legacy-mode handling based
    on whether the evaluable has ``dependency_input`` in its metadata.
    """
    dependency_input = _get_dependency_input(evaluable)
    if dependency_input is not None:
        # New mode: use wrap registry for input injection / output capture
        return await _run_entry_new_mode(
            evaluable, evaluator_names, runnable, semaphore, dependency_input
        )

    # Legacy mode: pass eval_input to runnable, use return value as eval_output
    async with semaphore:
        if inspect.iscoroutinefunction(runnable):
            output = await runnable(evaluable.eval_input)
        else:
            output = runnable(evaluable.eval_input)
    evaluable = evaluable.model_copy(update={"eval_output": output})

    evaluators = [_resolve_evaluator(name) for name in evaluator_names]
    short_names = [_short_name(n) for n in evaluator_names]

    evals: list[Evaluation] = list(
        await asyncio.gather(*(evaluate(ev, evaluable) for ev in evaluators))
    )

    exp_out = evaluable.expected_output
    expected_output = (
        None if isinstance(exp_out, _Unset) or exp_out is None else exp_out
    )

    eval_results = [
        EvaluationResult(
            evaluator=name,
            score=ev.score,
            reasoning=ev.reasoning,
        )
        for name, ev in zip(short_names, evals, strict=True)
    ]

    return EntryResult(
        input=evaluable.eval_input,
        output=evaluable.eval_output,
        expected_output=expected_output,
        description=evaluable.description,
        evaluations=eval_results,
    )


async def _run_dataset(dataset_path: Path) -> DatasetResult:
    """Run evaluations for a single dataset and return a DatasetResult.

    Entries run concurrently (gated by a semaphore for runnables).
    Evaluators within each entry also run concurrently.
    Rate limiting is enforced inside ``evaluate()`` when configured.
    """
    loaded = load_dataset_entries(dataset_path)
    runnable = _resolve_runnable(loaded.runnable)
    semaphore = asyncio.Semaphore(_get_runnable_concurrency())

    entry_tasks = [
        _run_entry(evaluable, evaluator_names, runnable, semaphore)
        for evaluable, evaluator_names in loaded.entries
    ]
    entry_results: list[EntryResult] = list(await asyncio.gather(*entry_tasks))

    return DatasetResult(dataset=loaded.name, entries=entry_results)


def _run_dataset_mode(
    path: str,
    *,
    verbose: bool = False,
    no_open: bool = False,
    argv: list[str] | None = None,
) -> int:
    """Execute dataset-driven mode: find datasets, run evals, save result JSON."""
    dataset_files = discover_dataset_files(path)
    if not dataset_files:
        print("No dataset files found.")  # noqa: T201
        return 1

    raw_argv = argv if argv is not None else sys.argv[1:]
    command_str = "pixie test " + " ".join(raw_argv)

    test_id = generate_test_id()
    started_at = datetime.now(timezone.utc).isoformat()
    all_passed = True
    dataset_results: list[DatasetResult] = []

    for ds_path in dataset_files:
        try:
            ds_result = asyncio.run(_run_dataset(ds_path))
        except ValueError as exc:
            print(str(exc))  # noqa: T201
            return 1
        dataset_results.append(ds_result)

        # Print results
        passed_count = sum(
            1
            for entry in ds_result.entries
            if all(ev.score >= 0.5 for ev in entry.evaluations)
        )
        total_count = len(ds_result.entries)
        print(f"\n{'=' * 52} {ds_result.dataset} {'=' * 52}")  # noqa: T201
        for i, entry in enumerate(ds_result.entries):
            evals_str = ", ".join(ev.evaluator for ev in entry.evaluations)
            scores = [f"{ev.score:.2f}" for ev in entry.evaluations]
            all_pass = all(ev.score >= 0.5 for ev in entry.evaluations)
            mark = "\u2713" if all_pass else "\u2717"
            desc = entry.description or str(entry.input)
            if len(desc) > 80:
                desc = desc[:80] + "…"
            print(  # noqa: T201
                f"  [{i+1}] {desc} ({evals_str}) [{', '.join(scores)}] {mark}"
            )
            if not all_pass:
                all_passed = False
                if verbose:
                    for ev in entry.evaluations:
                        if ev.score < 0.5:
                            print(f"      {ev.evaluator}: {ev.reasoning}")  # noqa: T201

        print(f"  {passed_count}/{total_count} passed")  # noqa: T201

    ended_at = datetime.now(timezone.utc).isoformat()
    run_result = RunResult(
        test_id=test_id,
        command=command_str,
        started_at=started_at,
        ended_at=ended_at,
        datasets=dataset_results,
    )
    result_path = save_test_result(run_result)
    print(f"\nResults saved to {result_path}")  # noqa: T201

    if not no_open:
        from pixie.config import get_config
        from pixie.web.server import open_webui

        config = get_config()
        open_webui(
            config.root,
            tab="results",
            item_id=f"results/{test_id}",
        )

    return 0 if all_passed else 1


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``pixie test`` command.

    Args:
        argv: Command-line arguments. Defaults to ``sys.argv[1:]``.

    Returns:
        Exit code: 0 if all tests pass, 1 otherwise.
    """
    parser = argparse.ArgumentParser(
        prog="pixie test",
        description="Run pixie eval tests",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help=(
            "File or directory. .json files trigger dataset mode. "
            "Omit to search the pixie datasets directory."
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Show detailed evaluation results",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        default=False,
        help="Do not automatically open the scorecard HTML in a browser",
    )

    args = parser.parse_args(argv)

    # Ensure instrumentation is initialised before running test functions
    px.init()
    configure_rate_limits_from_config()

    # Determine mode
    if args.path is None:
        # No argument: search pixie datasets directory
        from pixie.config import get_config

        config = get_config()
        return _run_dataset_mode(
            config.dataset_dir,
            verbose=args.verbose,
            no_open=args.no_open,
            argv=argv,
        )

    return _run_dataset_mode(
        args.path,
        verbose=args.verbose,
        no_open=args.no_open,
        argv=argv,
    )


if __name__ == "__main__":
    sys.exit(main())
