# Test Harness Redesign — Dataset-Driven Test Execution

## What Changed

### Phase 1: Dataset-Driven Mode

Added dataset-driven test execution mode to `pixie test`. Users can specify
evaluators directly in the dataset JSON file (per-row `evaluators` field) and
run `pixie test dataset.json` without writing any test functions.

### Phase 2: Evaluator Naming, JSON Arrays, CLI Modes, Per-Dataset Scorecards

1. **Removed `Eval` suffix from built-in evaluator names** — all 20 built-in
   evaluator factory functions renamed (e.g. `FactualityEval` → `Factuality`,
   `ExactMatchEval` → `ExactMatch`). `LevenshteinMatch` unchanged (had no suffix).

2. **Changed evaluators format to JSON array** — the `evaluators` field on
   `Evaluable` is now `list[str] | None` (was `str | None`). Dataset items use
   a JSON array like `["Factuality", "ClosedQA"]` instead of comma-separated
   strings. Bare built-in names are auto-resolved to `pixie.{Name}`.

3. **CLI supports three modes** — `pixie test dataset.json` (single file),
   `pixie test dir/` (all datasets in directory tree), and `pixie test` with no
   argument (all datasets in the pixie `dataset_dir`).

4. **Per-dataset scorecards** — each dataset generates its own `DatasetScorecard`
   with a 2D structure (`DatasetEntryResult[]`, each with non-uniform `Evaluation[]`).
   New models: `DatasetEntryResult`, `DatasetScorecard`. New functions:
   `save_dataset_scorecard()`, `generate_dataset_scorecard_html()`.

## Files Affected

- `pixie/evals/scorers.py` — Renamed 20 evaluator factory functions (removed `Eval` suffix)
- `pixie/__init__.py` — Updated all evaluator imports and `__all__`
- `pixie/evals/__init__.py` — Updated all evaluator imports and `__all__`
- `pixie/storage/evaluable.py` — Changed `evaluators` field type to `list[str] | None`
- `pixie/evals/dataset_runner.py` — Rewritten: `BUILTIN_EVALUATOR_NAMES` registry, `resolve_evaluator_name()`, `discover_dataset_files()`, `load_dataset_entries()`
- `pixie/cli/test_command.py` — Rewritten for three CLI modes: `_is_dataset_mode()`, `_run_dataset()`, `_run_dataset_mode()`
- `pixie/evals/scorecard.py` — Added `DatasetEntryResult`, `DatasetScorecard`, `save_dataset_scorecard()`, `generate_dataset_scorecard_html()`
- `tests/pixie/evals/test_dataset_runner.py` — Rewritten: 31 tests for new API
- `tests/pixie/evals/test_scorers.py` — Updated evaluator names in tests
- `tests/pixie/test_init.py` — Updated evaluator import tests
- `tests/pixie/cli/test_test_command.py` — Updated for new CLI default behavior
- `specs/test-harness-redesign.md` — Updated with new architecture details

## Migration Notes

- **Breaking**: Built-in evaluator names no longer have the `Eval` suffix. Update any imports:
  `from pixie import FactualityEval` → `from pixie import Factuality`
- **Breaking**: The `evaluators` field on `Evaluable` changed from `str | None` to `list[str] | None`.
  Update dataset JSON from `"evaluators": "pixie.FactualityEval"` to `"evaluators": ["Factuality"]`.
- **Breaking**: `pixie test` with no arguments now searches for dataset files in the pixie `dataset_dir`
  instead of discovering test files in the current directory. Pass `"."` explicitly for old behavior.
- Custom evaluator classes (`MockFactualityEval`, `SimpleFactualityEval`, etc.) are unaffected.
- The old grouping-by-evaluator-set approach is removed. Each row is now evaluated independently
  with its own evaluator set, producing non-uniform evaluator columns per entry.
