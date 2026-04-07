# API Docs Pre-Commit Generation

## Goal

Keep Python API documentation in sync with source code by generating docs automatically at commit time.

## Decision

- Use `pdoc3` to generate Markdown API docs.
- Generate docs into `docs/` (rooted at `docs/pixie/`).
- Replace the legacy custom generator script with a single deterministic command.
- Run generation from a local pre-commit hook.

## Hook Design

- Hook id: `generate-python-api-docs`
- Config file: `.pre-commit-config.yaml`
- Entry command: `scripts/generate_api_docs.sh`
- `pass_filenames: false` so docs are always regenerated from package state.

## Generation Script

`scripts/generate_api_docs.sh` performs:

1. Resolve repository root.
2. Remove existing `docs/` content.
3. Recreate `docs/`.
4. Run `uv run pdoc --force --output-dir docs pixie`.

## Expected Output

- `docs/pixie/index.md`
- Submodule docs under `docs/pixie/**`.

## Tradeoffs

- Full regeneration guarantees freshness but rewrites docs on every commit.
- `pdoc3` may emit non-fatal runtime warnings for deprecated third-party APIs during import.
