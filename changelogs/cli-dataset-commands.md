# CLI Dataset Commands

## What Changed

Added two CLI commands under `pixie dataset` for saving span data from the
observation store to datasets:

- **`pixie dataset create <name> --trace-id <id>`** — creates a new dataset
  containing the root span of the given trace, converted to an `Evaluable` item.
- **`pixie dataset append <name> --trace-id <id>`** — appends the root span of
  the given trace as an `Evaluable` item to an existing dataset.

A new `pixie` entry point is registered in `pyproject.toml`, providing
top-level subcommand routing via `pixie.cli.main`.

## Files Affected

- `pixie/cli/__init__.py` — updated docstring
- `pixie/cli/main.py` — **new** — main CLI entry point with argparse subcommands
- `pixie/cli/dataset_command.py` — **new** — `dataset_create()` and `dataset_append()` async functions
- `pyproject.toml` — added `pixie` script entry point
- `tests/pixie/cli/__init__.py` — **new** — test package marker
- `tests/pixie/cli/test_dataset_command.py` — **new** — unit tests for dataset commands
- `tests/pixie/cli/test_main.py` — **new** — integration tests for the CLI entry point
- `README.md` — documented new CLI commands
- `changelogs/cli-dataset-commands.md` — this file

## Migration Notes

- No breaking changes. The existing `pixie-test` entry point remains unchanged.
- A new `pixie` CLI entry point is now available. Use `pixie dataset create`
  and `pixie dataset append` to manage datasets from the command line.
