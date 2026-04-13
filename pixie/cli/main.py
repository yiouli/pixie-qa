"""``pixie`` CLI entry point — top-level command with subcommand routing.

Usage::

    pixie test [path] [-v] [--no-open]
    pixie trace --runnable <ref> --input <file> --output <file>
    pixie format --input <file> --output <file>
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

    # -- pixie stop ---------------------------------------------------------
    stop_parser = subparsers.add_parser("stop", help="Stop the running web UI server")
    stop_parser.add_argument(
        "root",
        nargs="?",
        default=None,
        help="Artifact root directory (default: from PIXIE_ROOT or pixie_qa)",
    )

    # -- pixie trace --------------------------------------------------------
    trace_parser = subparsers.add_parser(
        "trace",
        help="Run a Runnable and capture trace output to a JSONL file",
    )
    trace_parser.add_argument(
        "--runnable",
        required=True,
        help="Runnable reference in filepath:name format",
    )
    trace_parser.add_argument(
        "--input",
        required=True,
        dest="trace_input",
        help="Path to JSON file containing kwargs for the runnable",
    )
    trace_parser.add_argument(
        "--output",
        required=True,
        dest="trace_output",
        help="Path for the JSONL trace output file",
    )

    # -- pixie format -------------------------------------------------------
    format_parser = subparsers.add_parser(
        "format",
        help="Convert a trace log into a dataset entry JSON object",
    )
    format_parser.add_argument(
        "--input",
        required=True,
        dest="format_input",
        help="Path to the JSONL trace file (produced by 'pixie trace')",
    )
    format_parser.add_argument(
        "--output",
        required=True,
        dest="format_output",
        help="Path for the output dataset entry JSON file",
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

    # Auto-start the web server for every command except init and stop.
    # This is a silent, non-blocking operation — it spawns the server in the
    # background without opening a browser.
    if args.command not in ("init", "start", "stop"):
        from pixie.config import get_config
        from pixie.web.server import ensure_server

        config = get_config()
        ensure_server(config.root)

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

    elif args.command == "init":
        from pixie.cli.init_command import init_pixie_dir

        result_path = init_pixie_dir(root=args.root)
        print(f"Initialized pixie directory at {result_path}")  # noqa: T201

    elif args.command == "start":
        from pixie.cli.start_command import start

        return start(root=args.root)

    elif args.command == "stop":
        from pixie.cli.stop_command import stop

        return stop(root=args.root)

    elif args.command == "trace":
        from pixie.cli.trace_command import main as trace_main

        trace_argv = [
            "--runnable",
            args.runnable,
            "--input",
            args.trace_input,
            "--output",
            args.trace_output,
        ]
        return trace_main(trace_argv)

    elif args.command == "format":
        from pixie.cli.format_command import main as format_main

        format_argv = [
            "--input",
            args.format_input,
            "--output",
            args.format_output,
        ]
        return format_main(format_argv)

    return 0


if __name__ == "__main__":
    sys.exit(main())
