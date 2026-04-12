# Remove input_data duplication from dataset eval_input

## What changed

Previously, `input_data` was duplicated into `eval_input` at dataset creation
time (in `pixie format`), requiring every dataset entry to carry a redundant
`NamedData(name="input_data", value=...)` item. This made the dataset format
unnecessarily verbose and forced `eval_input` to always have at least one item.

Now, `input_data` is injected into `eval_input` at evaluation time by the
runner (`_run_entry`), just before constructing the `Evaluable`. This means:

- **`eval_input` in dataset entries is optional** (defaults to `[]`)
- **`input_data` is no longer duplicated** in the dataset JSON
- **Evaluators still see `input_data`** as the first `eval_input` item — the
  runner prepends it automatically

### Model changes

- `TestCase.eval_input` changed from `Field(min_length=1)` to default `[]`
- `Evaluable` added a `_require_eval_input` model validator to ensure evaluators
  always receive at least one input item (the runner guarantees this)

## Files affected

- `pixie/eval/evaluable.py` — relaxed `eval_input` on `TestCase`, added validator on `Evaluable`
- `pixie/harness/runner.py` — `_run_entry()` prepends `input_data` into `full_eval_input`
- `pixie/cli/format_command.py` — removed `INPUT_DATA_KEY` insertion into `eval_input`
- `pixie/instrumentation/models.py` — updated `INPUT_DATA_KEY` docstring
- `tests/pixie/eval/test_evaluable.py` — added tests for empty `eval_input` on `TestCase` and validation on `Evaluable`
- `tests/pixie/eval/test_dataset_runner.py` — added `TestRunDatasetInputDataInjection` tests; updated `_make_entry` helper
- `tests/pixie/cli/test_trace_format_commands.py` — updated assertions for new format output

## Migration notes

- Existing dataset files with `input_data` already in `eval_input` will still
  work — the runner prepends `input_data` regardless, so evaluators will see it
  twice (once injected, once from the dataset). To clean up, remove the
  `{"name": "input_data", "value": ...}` item from `eval_input` in existing
  datasets.
- Dataset entries may now omit `eval_input` entirely or use `"eval_input": []`.
