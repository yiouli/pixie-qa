# Dataset Runnable and Default Evaluators

## What Changed

Restored two capabilities that were lost when the test harness was simplified to run directly on datasets:

### 1. Dataset-level `runnable`

Datasets can now specify a top-level `"runnable"` field with a fully qualified function name (e.g. `"myapp.chat.ask_question"`). The evaluation harness resolves and calls this function with each item's `eval_input` to produce the `eval_output`, rather than using a static `eval_output` from the dataset. Both sync and async runnables are supported.

### 2. Dataset-level default evaluators

Datasets can now specify a top-level `"evaluators"` array as default evaluators for all items. Row-level evaluators are optional and override the defaults when present. The special value `"..."` in a row's evaluator list expands to all default evaluators, allowing rows to add extra evaluators without repeating the defaults.

### 3. `pixie evaluators list` command

New CLI subcommand that lists all available built-in evaluator names — helps users craft dataset JSON files.

### 4. Required dataset fields and validation command

- Top-level `runnable` is now required.
- Row-level `description` is now required for every dataset item.
- Added `pixie dataset validate [dir_or_dataset_path]` to validate dataset files with full error reporting.
- Validation checks:
  - Required properties (`runnable`, row `description`).
  - Runnable resolution to a callable.
  - Evaluator name resolution/importability.
  - At least one evaluator per row after applying dataset defaults and `"..."` expansion.

## Files Affected

- `pixie/evals/dataset_runner.py` — added `LoadedDataset` dataclass, `_resolve_runnable()`, `_expand_evaluator_names()`, `list_available_evaluators()`; changed `load_dataset_entries()` return type from tuple to `LoadedDataset`
- `pixie/cli/test_command.py` — updated `_run_dataset()` to use `LoadedDataset`, resolve and call runnable
- `pixie/cli/main.py` — added `evaluators list` subcommand
- `tests/pixie/evals/test_dataset_runner.py` — updated existing tests for new return type, added tests for `_expand_evaluator_names`, default evaluators, runnable field, `_resolve_runnable`, `list_available_evaluators`
- `docs/package.md` — documented dataset JSON schema, runnable, default evaluators, `pixie evaluators list`

## Migration Notes

- `load_dataset_entries()` now returns a `LoadedDataset` dataclass instead of a `tuple[str, list[...]]`. Access `.name`, `.runnable`, and `.entries` attributes instead of tuple destructuring.
- Existing datasets must be updated to include top-level `runnable` and per-row `description`.
- Existing datasets may omit top-level `evaluators` only if each row defines evaluators that resolve to at least one evaluator.
