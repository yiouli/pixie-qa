# WrappedData model and dataset format cleanup

## What changed

Centralized wrap data serialization/deserialization into a single Pydantic model
`WrappedData` (renamed from `WrapLogEntry`). Removed the legacy dataset format
where `eval_input` was a plain dict passed directly to the runnable.

### Key changes

- **`WrapLogEntry` renamed to `WrappedData`**: `WrapLogEntry` is kept as a
  backward-compatible type alias.
- **`parse_wrapped_data_list()` added**: Validates raw JSON from dataset
  `eval_input` columns into `list[WrappedData]` with clear error messages.
- **`Evaluable.get_wrap_inputs()` removed**: Parsing logic moved out of the
  data carrier into `test_command.py`.
- **Two execution modes only** in `_run_entry()`:
  - **Static mode**: `eval_output` is pre-computed in the dataset item — skip
    the runnable entirely.
  - **Wrap mode**: `eval_input` must be `list[WrappedData]` — parsed, split
    into entry/input registries, runnable called with entry data.
- **Legacy mode removed**: The old path that passed `eval_input` as a plain
  dict to the runnable no longer exists.
- **Exports updated**: `WrappedData` and `parse_wrapped_data_list` exported
  from `pixie` and `pixie.instrumentation`.

## Files affected

- `pixie/instrumentation/wrap_log.py` — renamed model, added parse function
- `pixie/storage/evaluable.py` — removed `get_wrap_inputs()`
- `pixie/cli/test_command.py` — rewrote entry processing pipeline
- `pixie/__init__.py` — added exports
- `pixie/instrumentation/__init__.py` — added exports
- `pixie/evals/dataset_runner.py` — updated docstring
- `tests/pixie/instrumentation/test_wrap_log.py` — new test file (13 tests)
- `tests/pixie/web/test_app.py` — updated fixtures for static mode

## Migration notes

- `WrapLogEntry` still works as a type alias for `WrappedData`.
- Datasets using plain-dict `eval_input` without `eval_output` will now raise
  `ValueError`. Either:
  - Convert `eval_input` to `list[WrappedData]` format, or
  - Pre-compute `eval_output` in the dataset (static mode).
- `Evaluable.get_wrap_inputs()` no longer exists. Use
  `parse_wrapped_data_list(evaluable.eval_input)` instead.
