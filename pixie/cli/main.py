"""``pixie`` CLI entry point — top-level command with subcommand routing.

Usage::

    pixie dataset create <name>
    pixie dataset list
    pixie dataset save <name> [--select MODE] [--span-name NAME]
                               [--expected-output] [--notes TEXT]

Reads spans from the observation store (SQLite, configured via ``PIXIE_DB_PATH``)
and writes evaluable items to the dataset store (JSON files, configured via
``PIXIE_DATASET_DIR``).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import TextIO

from dotenv import load_dotenv
from piccolo.engine.sqlite import SQLiteEngine
from pydantic import JsonValue

from pixie.cli.dag_command import dag_check_trace, dag_validate
from pixie.cli.dataset_command import (
    dataset_create,
    dataset_list,
    dataset_save,
    format_dataset_table,
)
from pixie.cli.trace_command import trace_last, trace_list, trace_show, trace_verify
from pixie.config import get_config
from pixie.dataset.store import DatasetStore
from pixie.storage.evaluable import UNSET, _Unset
from pixie.storage.store import ObservationStore


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="pixie",
        description="Pixie — automated quality assurance for AI applications",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # -- pixie dataset -------------------------------------------------------
    dataset_parser = subparsers.add_parser(
        "dataset", help="Dataset management commands"
    )
    dataset_sub = dataset_parser.add_subparsers(
        dest="dataset_action", help="Dataset actions"
    )

    # pixie dataset create <name>
    create_parser = dataset_sub.add_parser("create", help="Create a new empty dataset")
    create_parser.add_argument("name", help="Name for the new dataset")

    # pixie dataset list
    dataset_sub.add_parser("list", help="List all datasets")

    # pixie dataset save <name> [options]
    save_parser = dataset_sub.add_parser(
        "save",
        help="Save a span from the latest trace to a dataset",
    )
    save_parser.add_argument("name", help="Name of the dataset to save to")
    save_parser.add_argument(
        "--select",
        choices=["root", "last_llm_call", "by_name"],
        default="root",
        help="How to select the span from the trace (default: root)",
    )
    save_parser.add_argument(
        "--span-name",
        default=None,
        help="Span name to match (required when --select=by_name)",
    )
    save_parser.add_argument(
        "--expected-output",
        action="store_true",
        default=False,
        help="Read expected output JSON from stdin",
    )
    save_parser.add_argument(
        "--notes",
        default=None,
        help="Optional notes to attach to the evaluable metadata",
    )

    # -- pixie trace ---------------------------------------------------------
    trace_parser = subparsers.add_parser("trace", help="Inspect captured traces")
    trace_sub = trace_parser.add_subparsers(dest="trace_action", help="Trace actions")

    # pixie trace list [--limit N] [--errors]
    trace_list_parser = trace_sub.add_parser("list", help="List recent traces")
    trace_list_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of traces to show (default: 10)",
    )
    trace_list_parser.add_argument(
        "--errors",
        action="store_true",
        default=False,
        help="Show only traces with errors",
    )

    # pixie trace show <trace_id> [-v] [--json]
    trace_show_parser = trace_sub.add_parser("show", help="Show span tree for a trace")
    trace_show_parser.add_argument(
        "trace_id",
        help="Trace ID (or prefix, minimum 8 characters)",
    )
    trace_show_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Show full input/output data for each span",
    )
    trace_show_parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        default=False,
        help="Output as JSON",
    )

    # pixie trace last [--json]
    trace_last_parser = trace_sub.add_parser(
        "last", help="Show the most recent trace (verbose)"
    )
    trace_last_parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        default=False,
        help="Output as JSON",
    )

    # pixie trace verify
    trace_sub.add_parser(
        "verify",
        help="Verify the most recent trace for common instrumentation issues",
    )

    # -- pixie test ----------------------------------------------------------
    test_parser = subparsers.add_parser("test", help="Run pixie eval tests")
    test_parser.add_argument(
        "test_path",
        nargs="?",
        default=".",
        help="File or directory to search for tests (default: current directory)",
    )
    test_parser.add_argument(
        "-k",
        "--filter",
        dest="filter_pattern",
        default=None,
        help="Only run tests whose names contain this substring",
    )
    test_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Show detailed evaluation results",
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

    # -- pixie dag -----------------------------------------------------------
    dag_parser = subparsers.add_parser(
        "dag", help="Data-flow DAG validation and trace checking"
    )
    dag_sub = dag_parser.add_subparsers(dest="dag_action", help="DAG actions")

    # pixie dag validate <json_file> [--project-root PATH]
    dag_validate_parser = dag_sub.add_parser(
        "validate",
        help="Validate a DAG JSON file and generate Mermaid diagram",
    )
    dag_validate_parser.add_argument("json_file", help="Path to the DAG JSON file")
    dag_validate_parser.add_argument(
        "--project-root",
        default=None,
        help="Project root for resolving code pointers (default: JSON file directory)",
    )

    # pixie dag check-trace <json_file>
    dag_check_parser = dag_sub.add_parser(
        "check-trace",
        help="Check the last trace against a DAG JSON file",
    )
    dag_check_parser.add_argument("json_file", help="Path to the DAG JSON file")

    return parser


def _run_dataset_create(name: str) -> None:
    """Run dataset_create."""
    ds_store = DatasetStore()
    dataset = dataset_create(name=name, dataset_store=ds_store)
    print(f"Created dataset {dataset.name!r}.")  # noqa: T201


def _run_dataset_list() -> None:
    """Run dataset_list and print the table."""
    ds_store = DatasetStore()
    rows = dataset_list(dataset_store=ds_store)
    print(format_dataset_table(rows))  # noqa: T201


def _run_dataset_save(
    name: str,
    select: str,
    span_name: str | None,
    expected_output_flag: bool,
    notes: str | None,
    stdin: TextIO | None = None,
) -> None:
    """Set up stores and run dataset_save."""
    config = get_config()
    engine = SQLiteEngine(path=config.db_path)
    obs_store = ObservationStore(engine=engine)
    ds_store = DatasetStore()

    expected: JsonValue | _Unset = UNSET
    if expected_output_flag:
        source = stdin if stdin is not None else sys.stdin
        raw = source.read().strip()
        if not raw:
            raise ValueError(
                "--expected-output flag set but no JSON provided on stdin."
            )
        expected = json.loads(raw)

    dataset = asyncio.run(
        dataset_save(
            name=name,
            observation_store=obs_store,
            dataset_store=ds_store,
            select=select,
            span_name=span_name,
            expected_output=expected,
            notes=notes,
        )
    )
    print(  # noqa: T201
        f"Saved to dataset {dataset.name!r} — now {len(dataset.items)} item(s)."
    )


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

    if args.command == "dataset":
        if args.dataset_action is None:
            parser.parse_args(["dataset", "--help"])
            return 1

        try:
            if args.dataset_action == "create":
                _run_dataset_create(args.name)
            elif args.dataset_action == "list":
                _run_dataset_list()
            elif args.dataset_action == "save":
                _run_dataset_save(
                    name=args.name,
                    select=args.select,
                    span_name=args.span_name,
                    expected_output_flag=args.expected_output,
                    notes=args.notes,
                )
        except (
            ValueError,
            FileExistsError,
            FileNotFoundError,
            json.JSONDecodeError,
        ) as exc:
            print(f"Error: {exc}", file=sys.stderr)  # noqa: T201
            return 1

    elif args.command == "trace":
        if args.trace_action is None:
            parser.parse_args(["trace", "--help"])
            return 1

        try:
            if args.trace_action == "list":
                return trace_list(
                    limit=args.limit,
                    errors_only=args.errors,
                )
            elif args.trace_action == "show":
                return trace_show(
                    trace_id=args.trace_id,
                    verbose=args.verbose,
                    as_json=args.as_json,
                )
            elif args.trace_action == "last":
                return trace_last(as_json=args.as_json)
            elif args.trace_action == "verify":
                return trace_verify()
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)  # noqa: T201
            return 1

    elif args.command == "test":
        from pixie.cli.test_command import main as test_main

        # Forward args in the format test_command.main() expects
        test_argv: list[str] = [args.test_path]
        if args.filter_pattern:
            test_argv.extend(["-k", args.filter_pattern])
        if args.verbose:
            test_argv.append("-v")
        return test_main(test_argv)

    elif args.command == "init":
        from pixie.cli.init_command import init_pixie_dir

        result_path = init_pixie_dir(root=args.root)
        print(f"Initialized pixie directory at {result_path}")  # noqa: T201

    elif args.command == "start":
        from pixie.cli.start_command import start

        return start(root=args.root)

    elif args.command == "dag":
        if args.dag_action is None:
            parser.parse_args(["dag", "--help"])
            return 1

        try:
            if args.dag_action == "validate":
                return dag_validate(
                    json_file=args.json_file,
                    project_root=args.project_root,
                )
            elif args.dag_action == "check-trace":
                return dag_check_trace(json_file=args.json_file)
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)  # noqa: T201
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
