"""``pixie test`` CLI entry point.

Usage::

    pixie test [path] [--verbose] [--no-open]

Supports dataset-driven mode — each dataset JSON file specifies its evaluators per row.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone

from pixie.config import get_config
from pixie.eval.rate_limiter import configure_rate_limits_from_config
from pixie.harness.run_result import (
    DatasetResult,
    RunResult,
    generate_test_id,
    save_test_result,
)
from pixie.harness.runner import discover_dataset_files, run_dataset
from pixie.web import server as web_server


async def _run_datasets(
    dataset_dir: str,
    *,
    verbose: bool = False,
    no_open: bool = False,
    argv: list[str] | None = None,
) -> int:
    """Execute dataset-driven mode: find datasets, run evals, save result JSON.

    Orchestrates multiple datasets, formats console output, saves results
    to the results directory, and optionally opens the web UI.

    Args:
        dataset_dir: Directory or file path to dataset(s).
        verbose: Whether to show detailed evaluation reasoning for failed items.
        no_open: Whether to skip opening the web UI.
        argv: Original command-line arguments for the command string.

    Returns:
        Exit code: 0 if all tests pass, 1 otherwise.
    """
    dataset_files = discover_dataset_files(dataset_dir)
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
            dataset_name, entry_results = await run_dataset(str(ds_path))
        except ValueError as exc:
            print(str(exc))  # noqa: T201
            return 1

        ds_result = DatasetResult(dataset=dataset_name, entries=entry_results)
        dataset_results.append(ds_result)

        # Print results
        passed_count = sum(
            1 for entry in ds_result.entries if all(ev.score >= 0.5 for ev in entry.evaluations)
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
                f"  [{i + 1}] {desc} ({evals_str}) [{', '.join(scores)}] {mark}"
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
        web_server.open_webui(
            get_config().root,
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

    dataset_dir = args.path or get_config().dataset_dir
    return asyncio.run(
        _run_datasets(
            dataset_dir,
            verbose=args.verbose,
            no_open=args.no_open,
            argv=argv,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
