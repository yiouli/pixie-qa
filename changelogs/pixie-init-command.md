# pixie init CLI command

## What changed

Added `pixie init` command to scaffold the standard `pixie_qa/` working directory
for eval-driven development. The command creates:

- `pixie_qa/` root directory
- `pixie_qa/datasets/` — for golden dataset JSON files
- `pixie_qa/tests/` — for eval test files
- `pixie_qa/scripts/` — for run_app.py, build_dataset.py, etc.
- `pixie_qa/MEMORY.md` — template for eval working notes

The command is idempotent: existing files and directories are never overwritten
or deleted. Respects the `PIXIE_ROOT` environment variable and accepts an
optional positional argument for a custom root path.

## Files affected

- `pixie/cli/init_command.py` — new module implementing `init_pixie_dir()`
- `pixie/cli/main.py` — wired up `pixie init` subcommand
- `tests/pixie/cli/test_init_command.py` — 6 tests for the init command
- `docs/package.md` — added Project Scaffolding section

## Migration notes

None — purely additive. No existing behavior changed.
