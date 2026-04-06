"""``pixie`` CLI entry point — top-level command with subcommand routing.

Usage::

    pixie test [path] [-v] [--no-open]
    pixie analyze <test_run_id>
    pixie init [root]
    pixie start [root]
"""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="pixie",
        description="Pixie — automated quality assurance for AI applications",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # -- pixie test ----------------------------------------------------------
    test_parser = subparsers.add_parser("test", help="Run pixie eval tests")
    test_parser.add_argument(
        "test_path",
        nargs="?",
        default=None,
        help="Dataset file or directory (default: pixie datasets directory)",
    )
    test_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Show detailed evaluation results",
    )
    test_parser.add_argument(
        "--no-open",
        action="store_true",
        default=False,
        help="Do not automatically open the scorecard HTML in a browser",
    )

    # -- pixie analyze -------------------------------------------------------
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Generate analysis and recommendations for a test run",
    )
    analyze_parser.add_argument(
        "test_run_id",
        help="Test run ID (e.g. 20260403-120000)",
    )

    # -- pixie init ----------------------------------------------------------
    init_parser = subparsers.add_parser(
        "init", help="Scaffold the pixie_qa working directory"
    )
    init_parser.add_argument(
        "root",
        nargs="?",
        default=None,
        help="Root directory to create (default: from PIXIE_ROOT or pixie_qa)",
    )

    # -- pixie start --------------------------------------------------------
    start_parser = subparsers.add_parser(
        "start", help="Launch the web UI for browsing eval artifacts"
    )
    start_parser.add_argument(
        "root",
        nargs="?",
        default=None,
        help="Artifact root directory (default: from PIXIE_ROOT or pixie_qa)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``pixie`` command.

    Args:
        argv: Command-line arguments. Defaults to ``sys.argv[1:]``.

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    load_dotenv()

    if args.command == "test":
        from pixie.cli.test_command import main as test_main

        # Forward args in the format test_command.main() expects
        test_argv: list[str] = []
        if args.test_path is not None:
            test_argv.append(args.test_path)
        if args.verbose:
            test_argv.append("-v")
        if args.no_open:
            test_argv.append("--no-open")
        return test_main(test_argv)

    elif args.command == "analyze":
        from pixie.cli.analyze_command import analyze

        return analyze(test_id=args.test_run_id)

    elif args.command == "init":
        from pixie.cli.init_command import init_pixie_dir

        result_path = init_pixie_dir(root=args.root)
        print(f"Initialized pixie directory at {result_path}")  # noqa: T201

    elif args.command == "start":
        from pixie.cli.start_command import start

        return start(root=args.root)

    return 0


if __name__ == "__main__":
    sys.exit(main())
