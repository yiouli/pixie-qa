# entry-kwargs-in-eval-input

## What changed

`pixie format` now always includes `input_data` as the first `eval_input`
item (under the reserved name `"input_data"`). Previously, it would raise
`ValueError("No input data found ...")` when the trace had no
`wrap(purpose="input")` events. This caused coding agents to waste turns
debugging a non-error.

### New constant: `INPUT_DATA_KEY`

`pixie.instrumentation.models.INPUT_DATA_KEY` (`"input_data"`) is the
reserved eval_input name for the runnable kwargs. It is also re-exported
from `pixie.instrumentation`.

### Name collision validation in `TraceLogProcessor`

`TraceLogProcessor.on_emit()` now tracks wrap names during a trace and raises
`WrapNameCollisionError` when:

- A wrap name equals the reserved `INPUT_DATA_KEY`
- A wrap name duplicates a previously-seen name in the same trace

`WrapNameCollisionError` is a new `ValueError` subclass exported from
`pixie.instrumentation`.

## Files affected

- `pixie/instrumentation/models.py` — added `INPUT_DATA_KEY` constant
- `pixie/instrumentation/wrap.py` — added `WrapNameCollisionError`, name
  validation in `TraceLogProcessor`
- `pixie/instrumentation/__init__.py` — re-exports for new symbols
- `pixie/cli/format_command.py` — always inserts kwargs into `eval_input`;
  removed the `ValueError` branch for empty input
- `tests/pixie/cli/test_trace_format_commands.py` — updated format tests
  (kwargs-only and empty-kwargs now succeed), added collision tests

## Migration notes

- `format_trace_to_entry()` no longer raises `ValueError` when there are no
  `wrap(purpose="input")` events. Code that caught this error can be removed.
- Wrap names that collide with `"input_data"` or with each other now raise
  `WrapNameCollisionError` during `pixie trace`. Rename conflicting wraps.
- Dataset entries produced by `pixie format` now have an extra leading item
  in `eval_input` (`{"name": "input_data", "value": {...}}`).
