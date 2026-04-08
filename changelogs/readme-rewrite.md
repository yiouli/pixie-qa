# README Rewrite

## What changed and why

The README was stale: it referenced the old `qa-eval` skill name (now `eval-driven-dev`),
omitted the full CLI surface (`pixie trace`, `pixie format`, `pixie analyze`), and gave no
explanation of the core `wrap()` / `Runnable` / dataset-JSON APIs that developers actually
interact with.

The README has been rewritten from scratch to accurately reflect the current state of
the project.

## Files affected

- `README.md` — full rewrite
- `specs/readme-rewrite.md` — new spec documenting what the README must cover
- `changelogs/readme-rewrite.md` — this changelog

## What's new in the README

- Clear two-tool overview: `eval-driven-dev` agent skill + `pixie-qa` Python package
- Correct skill name (`eval-driven-dev`) and install command (`npx skills add yiouli/pixie-qa`)
- Six-step eval-driven development workflow summary
- `wrap()` API with purpose table
- `Runnable` protocol with a working example
- Dataset JSON schema with a concrete example
- Evaluator reference table
- Full CLI reference table (`test`, `trace`, `format`, `analyze`, `init`, `start`)
- Configuration env-var table

## Migration notes

Documentation only — no API or behavior changes.
