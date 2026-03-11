# CLI Dataset Commands

## What Changed

Rewrote the `pixie dataset` CLI commands to match the intended design:

- **`pixie dataset create <name>`** — creates a new empty dataset (no longer
  requires `--trace-id`).
- **`pixie dataset list`** — lists all datasets in a CLI table showing name,
  row count, created date-time, and updated date-time.
- **`pixie dataset save <name>`** — gets the latest trace from the observation
  store, selects a span from it, and saves it as an evaluable item to the
  named dataset. Supports:
  - `--select {root,last_llm_call,by_name}` — span selection mode (default: root)
  - `--span-name NAME` — required when `--select=by_name`
  - `--expected-output` — reads JSON from stdin (supports piping)
  - `--notes TEXT` — attaches notes to the evaluable's metadata

Removed the old `pixie dataset append` command (replaced by `dataset save`).

## Files Affected

- `pixie/cli/__init__.py` — updated docstring
- `pixie/cli/main.py` — rewritten argparse with create, list, save subcommands
- `pixie/cli/dataset_command.py` — rewritten with dataset_create, dataset_list,
  dataset_save, format_dataset_table functions
- `tests/pixie/cli/test_dataset_command.py` — rewritten with 20 unit tests
- `tests/pixie/cli/test_main.py` — rewritten with 11 integration tests
- `README.md` — updated CLI documentation
- `changelogs/cli-dataset-commands.md` — this file

## Migration Notes

- **Breaking**: `pixie dataset create` no longer accepts `--trace-id`. It now
  creates an empty dataset. Use `pixie dataset save` to add items.
- **Breaking**: `pixie dataset append` has been removed. Use
  `pixie dataset save <name>` instead, which automatically uses the latest trace.
