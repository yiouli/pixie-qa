# Simplify wrap processors and registry

## What changed and why

Removed `TraceFileWriter` entirely and simplified the wrap registry from
complex capture registries to two simple context variables. Also
restructured tracing responsibility — `LLMSpanProcessor` and `run_utils`
no longer write to the trace log; tracing is now fully handled by
`trace_command.py` via `TraceLogProcessor` and an `LLMTraceLogger` handler.

### TraceFileWriter → TraceLogProcessor

The `TraceFileWriter` class was removed. `TraceLogProcessor` now writes
JSON lines directly to a file (thread-safe with a lock) instead of
delegating to a separate writer. It also exposes `write_line()` for
non-wrap records (kwargs, LLM spans).

### Tracing responsibility moved to trace_command

`LLMSpanProcessor.on_end()` no longer writes to the trace log.
`run_utils.run_runnable()` no longer writes kwargs to the trace log.
Instead, `trace_command.py` registers an `LLMTraceLogger` handler that
writes LLM span data via `TraceLogProcessor.write_line()`, and writes
kwargs directly before calling the runnable.

### init() → enable_llm_tracing()

`observation.init()` was renamed to `enable_llm_tracing()` and no longer
sets up trace file output — that is now handled exclusively by the
trace command.

### Registry simplification

The old registry had five context variables (`_input_registry`,
`_capture_registry`, `_output_capture_registry`, `_state_capture_registry`,
etc.) with corresponding getters/setters. This was replaced by two:

- `eval_input: ContextVar[dict[str, str] | None]` — input injection data
- `eval_output: ContextVar[list[dict] | None]` — collected wrap event bodies

The `EvalCaptureLogProcessor` now simply appends body dicts to `eval_output`
for `purpose="output"` and `purpose="state"` events.

### Registration guard

Added `ensure_eval_capture_registered()` to prevent duplicate
`EvalCaptureLogProcessor` registration on the shared `LoggerProvider`
(OTel processors are additive and cannot be removed).

### test_command uses WrappedData.model_validate()

`_run_entry()` now validates captured body dicts into `WrappedData`
via Pydantic's `model_validate()` instead of manual dict field access.
`deserialize_wrap_data` is no longer imported.

## Files affected

| File                                                  | Change                                                                                       |
| ----------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `pixie/instrumentation/trace_writer.py`               | **Deleted**                                                                                  |
| `pixie/instrumentation/observation.py`                | `init()` renamed to `enable_llm_tracing()`; trace file setup removed                         |
| `pixie/instrumentation/processor.py`                  | Removed trace log writing from `on_end()`                                                    |
| `pixie/instrumentation/wrap_registry.py`              | Rewritten: 2 context vars, 6 functions                                                       |
| `pixie/instrumentation/wrap_processors.py`            | `TraceLogProcessor` writes directly; `ensure_eval_capture_registered()` added                |
| `pixie/instrumentation/wrap.py`                       | Uses `get_eval_input()` instead of `get_input_registry()`                                    |
| `pixie/instrumentation/__init__.py`                   | Added `enable_llm_tracing`; updated exports                                                  |
| `pixie/__init__.py`                                   | Removed internal processor exports; `init` → `enable_llm_tracing`; added `UNSET`, `TestCase` |
| `pixie/evals/run_utils.py`                            | Removed trace log writing from `run_runnable()`                                              |
| `pixie/cli/trace_command.py`                          | Rewritten: `LLMTraceLogger` handler; uses `enable_llm_tracing()`                             |
| `pixie/cli/test_command.py`                           | Uses `ensure_eval_capture_registered()`; `WrappedData.model_validate()` for captured bodies  |
| `tests/pixie/instrumentation/test_wrap.py`            | Updated to new registry API                                                                  |
| `tests/pixie/instrumentation/test_wrap_processors.py` | Updated to new processor/registry API                                                        |
| `tests/pixie/instrumentation/test_wrap_registry.py`   | Rewritten for `eval_input`/`eval_output`                                                     |
| `tests/pixie/instrumentation/conftest.py`             | Uses `ensure_eval_capture_registered()`                                                      |
| `tests/pixie/cli/test_trace_format_commands.py`       | Uses `TraceLogProcessor.write_line()`                                                        |
| `tests/manual/verify_wrap_e2e.py`                     | Uses `TraceLogProcessor` instead of `TraceFileWriter`                                        |

## Migration notes

- `TraceFileWriter` no longer exists — use `TraceLogProcessor` directly
- `observation.init()` renamed to `enable_llm_tracing()`; no longer sets up trace output
- `LLMSpanProcessor` no longer writes to trace log — use `LLMTraceLogger` handler in `trace_command`
- `run_utils.run_runnable()` no longer writes kwargs — caller writes via `TraceLogProcessor.write_line()`
- Old registry functions (`set_input_registry`, `get_capture_registry`,
  `init_capture_registry`, etc.) are replaced by `set_eval_input`,
  `get_eval_input`, `clear_eval_input`, `init_eval_output`,
  `get_eval_output`, `clear_eval_output`
- `EvalCaptureLogProcessor` no longer deserializes data — it passes
  raw body dicts; `test_command` uses `WrappedData.model_validate()`
- `TraceLogProcessor`, `EvalCaptureLogProcessor`, `ensure_eval_capture_registered`
  removed from `pixie.__init__` public API (internal to instrumentation)
