# Web UI Bug Fixes

## What Changed

Fixed four issues in the pixie web UI dashboard:

### 1. JSON file rendering in Project Context tab
- **Problem**: `.json` files appeared in the sidebar but rendered empty content.
  The backend returns raw JSON for `.json` files, but the `CodePanel` component
  expected `{ content: string }`.
- **Fix**: Added a new `JsonPanel` component using `react18-json-view` that
  properly handles raw JSON responses with pretty-formatted, collapsible display.
- **Files**: `frontend/src/webui/components/JsonPanel.tsx` (new),
  `frontend/src/webui/components/ProjectContextPanel.tsx`

### 2. Dataset rendering showing "Dataset is empty"
- **Problem**: Dataset files have `entries` as the key for their items array,
  but the frontend expected `items`.
- **Fix**: Normalised the API response to accept both `items` and `entries`,
  with a fallback name derived from the file path.
- **Files**: `frontend/src/webui/components/DatasetsPanel.tsx`

### 3. Analysis in scorecard not auto-updating
- **Problem**: When analysis markdown files were written to disk, the SSE
  `file_change` event was received but the `ResultsPanel` didn't re-fetch
  because `selected` didn't change.
- **Fix**: Added a `resultVersion` counter in `WebUIApp` that increments on
  any `results/` file change. Passed as a dependency to the fetch `useEffect`
  in `ResultsPanel`.
- **Files**: `frontend/src/webui/WebUIApp.tsx`,
  `frontend/src/webui/components/ResultsPanel.tsx`

### 4. Warning color for borderline evaluator scores
- **Problem**: Scores ≥0.5 but ≤0.6 showed green (pass) even though they are
  borderline.
- **Fix**: Added a warning tier (amber) to the design tokens and a `scoreTier()`
  helper. Scores ≥0.5 and ≤0.6 now display with warning colour. The entry row
  shows a "WARN" badge when all evals pass but any is in the warning range.
- **Files**: `frontend/src/webui/tailwind.css`,
  `frontend/src/webui/components/ResultsPanel.tsx`

## Dependencies Added
- `react18-json-view@^0.2.10` — collapsible JSON viewer for React 18+

## Migration Notes
None — these are bug fixes with no API changes.
