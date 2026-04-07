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

from pydantic import BaseModel

from pixie.eval.dataset_runner import (
    DatasetEntry,
    _resolve_evaluator,
    _resolve_runnable,
    _short_name,
    discover_dataset_files,
    load_dataset_entries,
)
from pixie.eval.evaluable import Evaluable, NamedData, _Unset
from pixie.eval.evaluation import Evaluation, evaluate
from pixie.eval.rate_limiter import configure_rate_limits_from_config
from pixie.harness.run_result import (
    DatasetResult,
    EntryResult,
    EvaluationResult,
    RunResult,
    generate_test_id,
    save_test_result,
)
from pixie.harness.runnable import get_runnable_args_type, is_runnable_class
from pixie.instrumentation.wrap import (
    WrappedData,
    WrapRegistryMissError,
    WrapTypeMismatchError,
    clear_eval_input,
    clear_eval_output,
    get_eval_output,
    init_eval_output,
    serialize_wrap_data,
    set_eval_input,
)


async def _evaluate_entry(
    evaluable: Evaluable,
    evaluator_names: list[str],
) -> EntryResult:
    """Run evaluators on a fully-populated evaluable and return an EntryResult."""
    evaluators = [_resolve_evaluator(name) for name in evaluator_names]
    short_names = [_short_name(n) for n in evaluator_names]

    evals: list[Evaluation] = list(
        await asyncio.gather(*(evaluate(ev, evaluable) for ev in evaluators))
    )

    exp_out = evaluable.expectation
    expectation = None if isinstance(exp_out, _Unset) or exp_out is None else exp_out

    eval_results = [
        EvaluationResult(
            evaluator=name,
            score=ev.score,
            reasoning=ev.reasoning,
        )
        for name, ev in zip(short_names, evals, strict=True)
    ]

    return EntryResult(
        input=evaluable.eval_input[0].value,
        output=evaluable.eval_output[0].value,
        expected_output=expectation,
        description=evaluable.description,
        evaluations=eval_results,
    )


async def _run_entry(
    entry: DatasetEntry,
    runnable: Callable[..., Any],
    semaphore: asyncio.Semaphore,
    *,
    args_type: type[BaseModel] | None = None,
) -> EntryResult:
    """Process a single dataset entry: call runnable, then evaluate.

    Sets up ``eval_input`` (for ``wrap(purpose="input")`` injection) and
    ``eval_output`` (populated by ``EvalCaptureLogProcessor``) before
    calling the runnable.  After the call, captured bodies are validated
    into :class:`WrappedData` and converted to :class:`NamedData`.

    When *args_type* is provided (Runnable protocol), kwargs are validated
    into the Pydantic model before calling the runnable.
    """
    test_case = entry.test_case

    async with semaphore:
        init_eval_output()

        # Set dependency inputs from test_case.eval_input
        dependency_registry: dict[str, str] = {
            nd.name: serialize_wrap_data(nd.value) for nd in test_case.eval_input
        }
        set_eval_input(dependency_registry)

        try:
            if args_type is not None:
                args = args_type.model_validate(entry.entry_kwargs)
                await runnable(args)
            elif inspect.iscoroutinefunction(runnable):
                await runnable(entry.entry_kwargs)
            else:
                runnable(entry.entry_kwargs)
        except (WrapRegistryMissError, WrapTypeMismatchError) as exc:
            clear_eval_input()
            clear_eval_output()
            return EntryResult(
                input=test_case.eval_input[0].value,
                output=None,
                expected_output=None,
                description=test_case.description,
                evaluations=[
                    EvaluationResult(
                        evaluator="WrapError",
                        score=0.0,
                        reasoning=str(exc),
                    )
                ],
            )

        captured = get_eval_output() or []
        clear_eval_input()
        clear_eval_output()

    # Build eval_output from runnable result and captured wrap events
    warpped_output = [
        WrappedData.model_validate(wrapped_raw) for wrapped_raw in captured
    ]
    eval_output = [
        NamedData(name=wrapped.name, value=wrapped.data) for wrapped in warpped_output
    ]

    evaluable = Evaluable(
        eval_input=test_case.eval_input,
        eval_output=eval_output,
        expectation=test_case.expectation,
        eval_metadata=test_case.eval_metadata,
        description=test_case.description,
    )

    return await _evaluate_entry(evaluable, entry.evaluators)


async def _run_dataset(dataset_path: Path) -> DatasetResult:
    """Run evaluations for a single dataset and return a DatasetResult.

    Entries run concurrently (gated by a semaphore for runnables).
    Evaluators within each entry also run concurrently.
    Rate limiting is enforced inside ``evaluate()`` when configured.

    When the dataset's runnable resolves to a :class:`Runnable` class,
    setup/teardown lifecycle hooks are called once around all entries,
    and each entry's kwargs are validated into the Runnable's args type.
    """
    dataset = load_dataset_entries(dataset_path)
    resolved = _resolve_runnable(dataset.runnable)
    semaphore = asyncio.Semaphore(4)

    if is_runnable_class(resolved):
        assert isinstance(resolved, type)  # narrow for type checker
        args_type = get_runnable_args_type(resolved)
        runnable_instance = resolved.create()  # type: ignore[attr-defined]
        try:
            await runnable_instance.setup()
            entry_tasks = [
                _run_entry(
                    entry,
                    runnable_instance.run,
                    semaphore,
                    args_type=args_type,
                )
                for entry in dataset.entries
            ]
            entry_results: list[EntryResult] = list(await asyncio.gather(*entry_tasks))
        finally:
            await runnable_instance.teardown()
    else:
        entry_tasks = [
            _run_entry(entry, resolved, semaphore) for entry in dataset.entries
        ]
        entry_results = list(await asyncio.gather(*entry_tasks))

    return DatasetResult(dataset=dataset.name, entries=entry_results)


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

    configure_rate_limits_from_config()

    # Register the eval capture processor so wrap() output/state events
    # are accumulated into eval_output for each entry run.
    from pixie.instrumentation.wrap import ensure_eval_capture_registered

    ensure_eval_capture_registered()

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
