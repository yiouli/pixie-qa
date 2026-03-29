# Task: Refactor Pixie's HTML report from inline Python strings to a compiled React app

## Context

Currently, the report HTML is assembled inline in Python by concatenating HTML strings with JSON data. We want to replace this with a proper React app that:

1. Gets developed as a React SPA with full devex (hot reload, component tooling, etc.)
2. Gets compiled into a **single self-contained HTML file** at build time
3. Ships inside the Python package as a static asset
4. At runtime, Python injects JSON data into the compiled HTML via string replacement

## Architecture

```txt
repo/
├── frontend/                     # React source (new)
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   └── ...components
│   ├── public/
│   │   └── mock-data.json      # Mock data for local dev
│   ├── index.html              # Vite entry with placeholder
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── pixie/
│   ├── assets/
│   │   └── index.html          # ← Vite builds here (gitignored)
│   └── ...
└── pyproject.toml
```

## React app requirements

- Use Vite + React + TypeScript
- Use `vite-plugin-singlefile` to produce a single `index.html` with all JS/CSS inlined
- The app reads data from `window.PIXIE_REPORT_DATA` (a global set before the app scripts run)
- In dev mode (`import.meta.env.DEV`), load from `/mock-data.json` instead so `vite dev` works standalone
- In `index.html`, include `<script>window.PIXIE_REPORT_DATA = "__PIXIE_DATA_PLACEHOLDER__";</script>` before the app script
- Vite build output goes to `../pixie/assets/`
- Create a `mock-data.json` that matches the shape of what the existing Python code currently injects — examine the existing report function to determine this schema
- Reproduce the existing report's functionality (layout, tables, data display) in React. Choose a modern lightweight UI approach (e.g., Tailwind + shadcn/ui, or whatever fits the scope of the report)

## Python side requirements

- Refactor the existing report generation function to:
  1. Read the compiled template from `pixie.assets/index.html` using `importlib.resources`
  2. Replace `"__PIXIE_DATA_PLACEHOLDER__"` (including the quotes) with `json.dumps(data)`
  3. Write the result to the output path
- Remove all the old inline HTML string assembly code
- Make sure `pyproject.toml` includes `pixie/assets/` in package data

## Build integration

- Add a `frontend/package.json` script: `"build": "vite build"`
- Add a top-level note or Makefile target so the build step is clear: `cd frontend && npm run build` produces the asset before `python -m build`
- The built `pixie/assets/index.html` should be gitignored (it's a build artifact)

## Constraints

- The final report HTML must work when opened directly from the filesystem (`file://` protocol) — no fetch calls, no external CDN dependencies, everything inlined
- Keep the React app simple and maintainable — this is a report viewer, not a full web app
- Preserve all existing report functionality; don't drop any data that's currently displayed

## Steps

1. Examine the existing report generation code to understand the current HTML structure and data schema
2. Scaffold the React app in `frontend/`
3. Build the React components to replicate the existing report
4. Configure Vite for single-file output to `pixie/assets/`
5. Refactor the Python report function to use template + injection
6. Update `pyproject.toml` for package data
7. Verify: run `cd frontend && npm run build`, then run the Python report generation, open the output HTML in a browser and confirm it renders correctly
