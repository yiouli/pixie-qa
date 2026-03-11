"""``pixie`` CLI entry point — top-level command with subcommand routing.

Usage::

    pixie dataset create <name> --trace-id <trace_id>
    pixie dataset append <name> --trace-id <trace_id>

Reads spans from the observation store (SQLite, configured via ``PIXIE_DB_PATH``)
and writes evaluable items to the dataset store (JSON files, configured via
``PIXIE_DATASET_DIR``).
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from piccolo.engine.sqlite import SQLiteEngine

from pixie.cli.dataset_command import dataset_append, dataset_create
from pixie.config import get_config
from pixie.dataset.store import DatasetStore
from pixie.storage.store import ObservationStore


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="pixie",
        description="Pixie — automated quality assurance for AI applications",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # -- pixie dataset -------------------------------------------------------
    dataset_parser = subparsers.add_parser("dataset", help="Dataset management commands")
    dataset_sub = dataset_parser.add_subparsers(
        dest="dataset_action", help="Dataset actions"
    )

    # pixie dataset create <name> --trace-id <id>
    create_parser = dataset_sub.add_parser(
        "create", help="Create a new dataset from a trace's root span"
    )
    create_parser.add_argument("name", help="Name for the new dataset")
    create_parser.add_argument(
        "--trace-id", required=True, help="Trace ID whose root span to save"
    )

    # pixie dataset append <name> --trace-id <id>
    append_parser = dataset_sub.add_parser(
        "append", help="Append a trace's root span to an existing dataset"
    )
    append_parser.add_argument("name", help="Name of the existing dataset")
    append_parser.add_argument(
        "--trace-id", required=True, help="Trace ID whose root span to save"
    )

    return parser


async def _run_dataset_create(name: str, trace_id: str) -> None:
    """Set up stores and run dataset_create."""
    config = get_config()
    engine = SQLiteEngine(path=config.db_path)
    obs_store = ObservationStore(engine=engine)
    ds_store = DatasetStore()

    dataset = await dataset_create(
        name=name,
        trace_id=trace_id,
        observation_store=obs_store,
        dataset_store=ds_store,
    )
    print(  # noqa: T201
        f"Created dataset {dataset.name!r} with {len(dataset.items)} item(s)."
    )


async def _run_dataset_append(name: str, trace_id: str) -> None:
    """Set up stores and run dataset_append."""
    config = get_config()
    engine = SQLiteEngine(path=config.db_path)
    obs_store = ObservationStore(engine=engine)
    ds_store = DatasetStore()

    dataset = await dataset_append(
        name=name,
        trace_id=trace_id,
        observation_store=obs_store,
        dataset_store=ds_store,
    )
    print(  # noqa: T201
        f"Appended to dataset {dataset.name!r} — now {len(dataset.items)} item(s)."
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

    if args.command == "dataset":
        if args.dataset_action is None:
            parser.parse_args(["dataset", "--help"])
            return 1

        try:
            if args.dataset_action == "create":
                asyncio.run(_run_dataset_create(args.name, args.trace_id))
            elif args.dataset_action == "append":
                asyncio.run(_run_dataset_append(args.name, args.trace_id))
        except (ValueError, FileExistsError, FileNotFoundError) as exc:
            print(f"Error: {exc}", file=sys.stderr)  # noqa: T201
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
