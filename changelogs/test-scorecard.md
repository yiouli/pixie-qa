# Test Scorecard Feature

## What Changed

Added an HTML scorecard report that is automatically generated and saved to disk
for every `pixie test` command run. The scorecard provides a detailed,
human-readable breakdown of eval-based test results beyond the terminal summary.

### Scorecard Contents

- **Test run overview** — command args, timestamp, pass/fail summary, and a
  table of all discovered tests with their status badges.
- **Per-test-function detail** — for each test that calls `assert_pass` or
  `assert_dataset_pass`:
  - Human-readable scoring strategy description.
  - Per-evaluator pass rate summary table.
  - Input × evaluator score grid with hover tooltips showing reasoning.
  - Tabbed view for multi-pass runs (one tab per pass).

### Scorecard Storage

HTML files are saved to `{config.root}/scorecards/<YYYYMMDD-HHMMSS-normalized-args>.html`.
The CLI prints the full path after each run so users can click to open it.

## Files Affected

### New Files

- `pixie/evals/scorecard.py` — data models (`AssertRecord`, `TestRecord`,
  `ScorecardReport`), `ScorecardCollector` (context-var-based accumulator),
  HTML generation, and `save_scorecard()`.
- `tests/pixie/evals/test_scorecard.py` — 28 tests covering models, collector,
  HTML generation, file saving, and integration with `assert_pass` / runner.

### Modified Files

- `pixie/evals/eval_utils.py` — `assert_pass` now publishes an `AssertRecord`
  to the active `ScorecardCollector` (no-op when no collector is active).
- `pixie/evals/runner.py` — `_run_single()` activates a `ScorecardCollector`
  per test; `EvalTestResult` gains an `assert_records` field.
- `pixie/cli/test_command.py` — builds a `ScorecardReport`, calls
  `save_scorecard()`, and prints the path.
- `pixie/evals/__init__.py` — re-exports `ScorecardCollector`,
  `ScorecardReport`, `generate_scorecard_html`, `save_scorecard`.
- `docs/package.md` — documents the HTML scorecard section under "Running Tests".

## Migration Notes

- No breaking API changes. Existing `pixie test` invocations behave identically
  to before, with the addition of an HTML file being written and a path printed
  at the end.
- `EvalTestResult.assert_records` defaults to an empty tuple, so any code
  that accesses `EvalTestResult` is unaffected.
- The scorecard directory (`{config.root}/scorecards/`) is created on demand.
