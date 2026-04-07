# pdoc async signatures

## What changed

- Added a custom pdoc markdown template at `scripts/pdoc_templates/text.mako`.
- Updated API markdown signature rendering to include the defining keyword (`def` or `async def`) for functions and methods.
- Updated `scripts/generate_api_docs.sh` to use the custom template via `--template-dir`.
- Updated root `README.md` to document why the custom template exists.

## Files affected

- `scripts/pdoc_templates/text.mako`
- `scripts/generate_api_docs.sh`
- `README.md`

## Migration notes

- No API/runtime behavior changes.
- If you generate docs manually, use `scripts/generate_api_docs.sh` (or pass `--template-dir scripts/pdoc_templates`) to preserve explicit async signatures.
