# pixie/assets

Static assets for the pixie Python package. This directory holds the compiled
React scorecard template used by `pixie.evals.scorecard.generate_scorecard_html()`.

## Contents

- **`index.html`** — Compiled single-file React application (build artifact,
  gitignored). Contains all JS, CSS, and markup inlined. At runtime, Python
  replaces the `"__PIXIE_DATA_PLACEHOLDER__"` string with serialized report data.

## Building

The template must be built from the frontend source before running tests or
building the Python package:

```bash
cd frontend && npm install && npm run build
```

This produces `pixie/assets/index.html`. The file is gitignored since it's a
build artifact — it's regenerated from `frontend/` source.

## How It's Loaded

`scorecard.py` uses `importlib.resources.files("pixie.assets")` to locate
`index.html` at runtime. The `pyproject.toml` `force-include` directive ensures
the file is included in the wheel even though the directory has no `__init__.py`.

## Development

To iterate on the scorecard UI, work in the `frontend/` directory — see
[frontend/README.md](../../frontend/README.md).
