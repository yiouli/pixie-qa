# Results Panel UI Fixes

## What changed

Four UI/backend issues in the Results Panel were fixed:

### 1. Pending evaluator styling (info color + clock icon)

- Added `info` color tokens (`--color-info`, `--color-info-bg`, `--color-info-border`, `--color-info-text`) to the Tailwind v4 theme — a blue palette (`#2563eb`) for informational/scheduled state.
- Replaced the Unicode hourglass character (`\u23f3`) with an inline SVG clock icon in the pending evaluator pill.
- Changed pending pill colors from gray/disabled (`border-border text-ink-muted`) to blue/info (`border-info-border text-info`) in both the table row pills and the detail modal.

### 2. Headline text clarity

- Changed the dataset pass/fail headline from `"{passed}/{total} passed | {pendingCount} pending"` (with mismatched smaller gray text for pending) to `"{passed} passed ({pendingCount} pending) of {total} total"` at consistent sizing with the pending count rendered in the info color.

### 3. SSE watcher for deep result files

- The file watcher (`_is_artifact`) only detected files at exactly depth 3 inside `results/` (e.g. `results/<id>/meta.json`). Files at depth 4+ like `results/<id>/dataset-0/entry-0/evaluations.jsonl` and `results/<id>/dataset-0/analysis.md` were never detected, so edits to evaluations and analysis files did not trigger UI updates via SSE.
- Changed the depth check from `len(parts) == 3` to `len(parts) >= 3` and added `.jsonl` to the accepted suffixes.

### 4. Action plan rendering

- Added `actionPlan?: string` field to `TestResultData` TypeScript type.
- Server's `/api/result` endpoint now reads `action-plan.md` from the test result root directory when present.
- `ResultView` component renders the action plan between the test overview card and dataset sections, styled like the dataset analysis (accent border-left, inset background).

## Files affected

- `frontend/src/webui/tailwind.css` — added info color tokens
- `frontend/src/webui/types.ts` — added `actionPlan` to `TestResultData`
- `frontend/src/webui/components/ResultsPanel.tsx` — pending pill styling, headline text, action plan rendering
- `pixie/web/watcher.py` — expanded `_is_artifact` to match deep result paths
- `pixie/web/app.py` — `api_result` reads `action-plan.md`
- `tests/pixie/web/test_watcher.py` — added 7 tests for deep result path detection
- `tests/pixie/web/test_app.py` — added 2 tests for action plan inclusion/omission

## Migration notes

None — all changes are backwards-compatible. The new `actionPlan` field is optional.
