# Scorecard Redesign — JSON Results and Analysis

## What Changed

Replaced the HTML scorecard generation pipeline with a structured JSON result system and added LLM-powered analysis.

### Test Results (JSON)

- `pixie test` now outputs results as JSON to `<PIXIE_ROOT>/results/<test_id>/result.json` instead of generating standalone HTML scorecards.
- The JSON schema includes meta (testId, command, timestamps), and per-dataset entries with evaluations (evaluator, score, reasoning).
- New data models: `EvaluationResult`, `EntryResult`, `DatasetResult`, `RunResult` in `pixie/evals/test_result.py`.

### `pixie analyze` Command

- New CLI command: `pixie analyze <test_run_id>` generates LLM-powered markdown analysis for each dataset in a test run.
- Uses OpenAI AsyncClient, model configurable via `PIXIE_ANALYZE_MODEL` env var (default: `gpt-4o-mini`).
- Analysis files saved as `dataset-<index>.md` alongside `result.json`.

### Description Field

- Added optional `description` field to `Evaluable` model in `pixie/storage/evaluable.py`.
- Updated sample datasets (`sample-qa.json`, `customer-faq.json`) with descriptions per entry.

### Web UI — Results Tab

- New "Results" tab (default) in the web UI showing test run overview, per-dataset analysis, and per-entry evaluation details.
- Server API: new `/api/result?id=<test_id>` endpoint serving result JSON with merged analysis markdown.
- Manifest now includes `results` key listing available test runs.
- File watcher detects changes in `results/` directory and sends SSE notifications.

### Frontend

- New `ResultsPanel` component with sidebar, result viewer, dataset sections, entry rows, and evaluation detail modal.
- Updated `WebUIApp.tsx` to default to Results tab.
- New TypeScript types for result data structures.

## Files Affected

### New Files

- `pixie/evals/test_result.py` — result data models and persistence
- `pixie/cli/analyze_command.py` — `pixie analyze` command
- `frontend/src/webui/components/ResultsPanel.tsx` — results panel UI
- `tests/pixie/evals/test_test_result.py` — result model tests (9 tests)
- `tests/pixie/cli/test_analyze_command.py` — analyze command tests (4 tests)

### Modified Files

- `pixie/storage/evaluable.py` — added `description` field
- `pixie/cli/test_command.py` — refactored to output JSON results
- `pixie/cli/main.py` — wired `analyze` subcommand
- `pixie/web/app.py` — added results endpoint and manifest key
- `pixie/web/watcher.py` — watches `results/` directory
- `frontend/src/webui/types.ts` — new result type definitions
- `frontend/src/webui/WebUIApp.tsx` — added Results tab
- `frontend/src/webui/webui.css` — results panel styles
- `tests/pixie/web/test_app.py` — updated for results API
- `tests/pixie/web/test_watcher.py` — tests for results artifact detection
- `tests/manual/datasets/sample-qa.json` — added description fields
- `tests/pixie/cli/e2e_fixtures/datasets/customer-faq.json` — added description fields
- `docs/package.md` — updated test results and web UI documentation
- `tests/README.md` — updated test file table and verification protocol
- `README.md` — added `pixie analyze` step

## Migration Notes

- `pixie test` no longer generates HTML scorecards. Old scorecards remain viewable in the Scorecards tab.
- The `description` field on dataset items is optional; existing datasets work without changes.
- `pixie analyze` requires an OpenAI API key (`OPENAI_API_KEY`) to generate analysis.
