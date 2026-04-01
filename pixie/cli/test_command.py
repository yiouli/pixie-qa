"""``pixie test`` CLI entry point.

Usage::

    pixie test [path] [--filter PATTERN] [--verbose] [--no-open]

Discovers and runs eval test functions, reporting pass/fail results.
Generates an HTML scorecard report saved to
``{config.root}/scorecards/<timestamp>.html`` and opens the web UI
to display it (pass ``--no-open`` to suppress).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import pixie.instrumentation as px
from pixie.evals.rate_limiter import configure_rate_limits_from_config
from pixie.evals.runner import discover_tests, format_results, run_tests
from pixie.evals.scorecard import ScorecardReport, TestRecord, save_scorecard


def _build_report(
    results: Sequence[object],
    command_args: str,
) -> ScorecardReport:
    """Build a :class:`ScorecardReport` from runner results.

    Args:
        results: List of ``EvalTestResult`` objects.
        command_args: The command-line arguments string.

    Returns:
        A fully populated ``ScorecardReport``.
    """
    from pixie.evals.runner import EvalTestResult

    test_records: list[TestRecord] = []
    for r in results:
        assert isinstance(r, EvalTestResult)
        test_records.append(
            TestRecord(
                name=r.name,
                status=r.status,
                message=r.message,
                asserts=list(r.assert_records),
            )
        )
    return ScorecardReport(command_args=command_args, test_records=test_records)


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
        default=".",
        help="File or directory to search for tests (default: current directory)",
    )
    parser.add_argument(
        "-k",
        "--filter",
        dest="filter_pattern",
        default=None,
        help="Only run tests whose names contain this substring",
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

    cases = discover_tests(args.path, filter_pattern=args.filter_pattern)
    results = run_tests(cases)
    output = format_results(results, verbose=args.verbose)
    print(output)  # noqa: T201

    # ── Generate and save scorecard ───────────────────────────────
    raw_argv = argv if argv is not None else sys.argv[1:]
    command_str = "pixie test " + " ".join(raw_argv)
    report = _build_report(results, command_args=command_str)
    scorecard_path = save_scorecard(report)
    print(f"\nSee {scorecard_path} for test details")  # noqa: T201

    if not args.no_open:
        from pixie.config import get_config
        from pixie.web.server import open_webui

        config = get_config()
        # Derive relative scorecard path within the artifact root
        scorecard_rel = str(Path(scorecard_path).relative_to(Path(config.root).resolve()))
        open_webui(config.root, tab="scorecards", item_id=scorecard_rel)

    all_passed = all(r.status == "passed" for r in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
