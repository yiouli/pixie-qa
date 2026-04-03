"""``pixie test`` CLI entry point.

Usage::

    pixie test [path] [--verbose] [--no-open]

Supports two modes:

1. **Dataset mode** — when *path* is a ``.json`` file or a directory
   containing dataset JSON files. Each dataset produces its own scorecard.
2. **Default** — no path searches the pixie datasets directory.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import pixie.instrumentation as px
from pixie.evals.dataset_runner import (
    _resolve_evaluator,
    _short_name,
    discover_dataset_files,
    load_dataset_entries,
)
from pixie.evals.evaluation import Evaluation, evaluate
from pixie.evals.rate_limiter import configure_rate_limits_from_config
from pixie.evals.scorecard import (
    DatasetEntryResult,
    DatasetScorecard,
    save_dataset_scorecard,
)


async def _run_dataset(dataset_path: Path) -> DatasetScorecard:
    """Run evaluations for a single dataset and return a scorecard."""
    dataset_name, entries = load_dataset_entries(dataset_path)

    results: list[DatasetEntryResult] = []
    for evaluable, evaluator_names in entries:
        evaluators = [_resolve_evaluator(name) for name in evaluator_names]
        short_names = tuple(_short_name(n) for n in evaluator_names)

        evals: list[Evaluation] = []
        for ev in evaluators:
            result = await evaluate(ev, evaluable)
            evals.append(result)

        input_label = str(evaluable.eval_input)
        if len(input_label) > 80:
            input_label = input_label[:80] + "…"

        from pixie.storage.evaluable import _Unset

        exp_out = evaluable.expected_output
        exp_str = (
            None if isinstance(exp_out, _Unset) or exp_out is None else str(exp_out)
        )

        results.append(
            DatasetEntryResult(
                evaluator_names=short_names,
                evaluations=tuple(evals),
                input_label=input_label,
                evaluable_dict={
                    "input": (
                        str(evaluable.eval_input)
                        if evaluable.eval_input is not None
                        else None
                    ),
                    "expected_output": exp_str,
                    "actual_output": (
                        str(evaluable.eval_output)
                        if evaluable.eval_output is not None
                        else None
                    ),
                    "metadata": evaluable.eval_metadata,
                },
            )
        )

    return DatasetScorecard(dataset_name=dataset_name, entries=results)


def _run_dataset_mode(
    path: str,
    *,
    verbose: bool = False,
    no_open: bool = False,
    argv: list[str] | None = None,
) -> int:
    """Execute dataset-driven mode: find datasets, run evals, generate scorecards."""
    dataset_files = discover_dataset_files(path)
    if not dataset_files:
        print("No dataset files found.")  # noqa: T201
        return 1

    raw_argv = argv if argv is not None else sys.argv[1:]
    command_str = "pixie test " + " ".join(raw_argv)
    all_passed = True

    for ds_path in dataset_files:
        scorecard = asyncio.run(_run_dataset(ds_path))

        # Print results
        print(f"\n{'=' * 52} {scorecard.dataset_name} {'=' * 52}")  # noqa: T201
        for i, entry in enumerate(scorecard.entries):
            evals_str = ", ".join(entry.evaluator_names)
            scores = [f"{e.score:.2f}" for e in entry.evaluations]
            all_pass = all(e.score >= 0.5 for e in entry.evaluations)
            mark = "\u2713" if all_pass else "\u2717"
            print(
                f"  [{i+1}] {entry.input_label} ({evals_str}) [{', '.join(scores)}] {mark}"
            )  # noqa: T201
            if not all_pass:
                all_passed = False
                if verbose:
                    for name, ev in zip(
                        entry.evaluator_names,
                        entry.evaluations,
                        strict=True,
                    ):
                        if ev.score < 0.5:
                            print(f"      {name}: {ev.reasoning}")  # noqa: T201

        # Generate scorecard
        scorecard_path = save_dataset_scorecard(scorecard, command_args=command_str)
        print(f"\nSee {scorecard_path} for details")  # noqa: T201

        if not no_open:
            from pixie.config import get_config
            from pixie.web.server import open_webui

            config = get_config()
            scorecard_rel = str(
                Path(scorecard_path).relative_to(Path(config.root).resolve())
            )
            open_webui(config.root, tab="scorecards", item_id=scorecard_rel)

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
