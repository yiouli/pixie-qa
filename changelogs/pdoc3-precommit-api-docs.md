# pdoc3 pre-commit API docs generation

## What changed

- Added a new pre-commit hook to auto-generate Python API docs from source code using `pdoc3`.
- Replaced the old custom script-based docs generator with a deterministic shell script.
- Regenerated and replaced existing `docs/` contents with `pdoc3` Markdown output under `docs/pixie/`.
- Added `pre-commit` and `pdoc3` as dev dependencies.

## Why

The previous custom doc generator was fragile and frequently produced stale docs. Regenerating docs during commit keeps API references aligned with code changes.

## Files affected

- `.pre-commit-config.yaml`
- `scripts/generate_api_docs.sh`
- `scripts/generate_skill_docs.py` (removed)
- `pyproject.toml`
- `uv.lock`
- `docs/` (replaced with generated Markdown docs)
- `README.md`
- `tests/README.md`
- `specs/api-docs-precommit.md`

## Migration notes

- Run `uv sync` to install updated dev dependencies.
- Run `uv run pre-commit install` once per local clone.
- The old manual command `uv run python scripts/generate_skill_docs.py` no longer exists.
