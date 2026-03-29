# Frontend Restructuring — Inline HTML → React SPA

## What Changed

Replaced the inline Python HTML generation in `pixie/evals/scorecard.py` with a
compiled React single-page application. The scorecard report is now a React 19 +
TypeScript app built with Vite, compiled to a single self-contained HTML file
using `vite-plugin-singlefile`, and shipped as a static asset inside the Python
package.

**Before:** ~700 lines of inline HTML/CSS/JS string concatenation in Python, with
`html.escape()` calls, embedded `<script>` blocks, and manual DOM construction.

**After:** A `frontend/` directory containing a standard React project. Python
loads the compiled template via `importlib.resources` and injects JSON data by
replacing a placeholder string. The scorecard module dropped from 916 → 362 lines.

## Architecture

```
frontend/                        # React source (new)
├── src/
│   ├── main.tsx                 # Entry point — loads data from window global or mock
│   ├── App.tsx                  # Root component with modal state
│   ├── types.ts                 # TypeScript interfaces matching Python models
│   ├── styles.css               # "Ink & Signal" design theme
│   └── components/
│       ├── BrandHeader.tsx      # Sticky header with pixie branding
│       ├── Overview.tsx         # Run overview card with summary table
│       ├── StatusBadge.tsx      # PASS/FAIL/ERROR badge
│       ├── TestSection.tsx      # Per-test card with assert results
│       ├── AssertCard.tsx       # Assert result with scoring strategy
│       ├── PassTable.tsx        # Evaluator summary + per-input score table
│       ├── EvalDetailModal.tsx  # Full evaluation detail modal
│       └── FeedbackModal.tsx    # User feedback form modal
├── public/
│   └── mock-data.json           # Realistic mock data for dev mode
├── package.json                 # React 19, Vite 6, vite-plugin-singlefile
├── tsconfig.json
└── vite.config.ts               # Output → ../pixie/assets/

pixie/assets/
└── index.html                   # Build artifact (gitignored)
```

**Data flow:**

1. `_report_to_dict()` serialises `ScorecardReport` → JSON-safe dict
2. `generate_scorecard_html()` loads compiled template, replaces
   `"__PIXIE_DATA_PLACEHOLDER__"` with `json.dumps(data)`
3. React reads `window.PIXIE_REPORT_DATA` and renders the report

## Files Affected

### New files

- `frontend/` — entire React project (17 files)
- `pixie/assets/index.html` — build artifact (gitignored)

### Modified files

- `pixie/evals/scorecard.py` — removed all inline HTML generation; added
  `_load_template()`, `_report_to_dict()`, and template-based
  `generate_scorecard_html()`
- `tests/pixie/evals/test_scorecard.py` — updated `TestGenerateScorecardHtml`
  to verify JSON data injection; added `TestReportToDict` (4 tests)
- `tests/pixie/cli/test_e2e_pixie_test.py` — updated branding assertion
  (`data-action` attribute → URL string check)
- `pyproject.toml` — added `[tool.hatch.build.targets.wheel.force-include]`
  for `pixie/assets/index.html`
- `.gitignore` — added `pixie/assets/index.html`, `frontend/node_modules/`,
  `frontend/dist/`

## Migration Notes

- **No API changes** — `generate_scorecard_html()` and `save_scorecard()` retain
  the same signatures and return types.
- **Build step required** — after cloning, run `cd frontend && npm install &&
npm run build` before `uv build` or running tests. The compiled
  `pixie/assets/index.html` must exist for `generate_scorecard_html()` to work.
- **Node.js 18+ required** for frontend development and builds.
- **Report HTML opens from `file://`** — no external CDN or fetch calls; the
  entire React app is inlined into a single HTML file.

## Design Theme

The new UI uses the "Ink & Signal" design language:

- Warm stone/cream background (`#faf9f7`)
- Monospace headings (JetBrains Mono stack)
- Serif body text (Charter/Georgia stack)
- Emerald pass (`#059669`), coral fail (`#dc2626`), purple accent (`#7c3aed`)
