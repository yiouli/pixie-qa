# Unified Per-Entry Trace Capture

## What changed

Refactored the `pixie test` trace capture system to produce **unified
per-entry trace files** that contain the full execution flow — entry kwargs,
all `wrap()` events (input, output, state), and LLM spans — in
chronological order.

### Architecture changes

- **`LLMSpanTrace` now subclasses `LLMSpanLog`** — eliminates field
  duplication; inherits `operation`, `provider`, `request_model`,
  `response_model`, `input_messages`, `output_messages`,
  `tool_definitions`, `finish_reasons`, `error_type` from the parent.
  The `type` Literal is overridden to `"llm_span_trace"`.

- **`TraceCaptureHandler` replaced by `EntryTraceCollector`** — the new
  class collects entry kwargs, wrap events, and LLM spans per entry.
  A backward-compat alias `TraceCaptureHandler = EntryTraceCollector`
  is provided.

- **`EntryTraceLogProcessor`** — new OTel `LogRecordProcessor` that
  intercepts `wrap()` emissions and routes them to the active
  `EntryTraceCollector`, stamping each with `captured_at`.

- **Module-level active collector** — `set_active_collector()`,
  `get_active_collector()`, and `record_entry_kwargs()` enable
  cross-module access from `runner.py` without direct coupling.

- **`wrap(purpose="input")` now emits in eval mode** — previously,
  eval-mode input injection returned the injected value without
  emitting. Now it also emits the wrap event so trace log processors
  see input data. `EvalCaptureLogProcessor` is unaffected (it only
  captures output/state).

### Trace file format

Each `{result_dir}/traces/entry-{i}.jsonl` now contains, in order:

1. `{"type": "kwargs", "value": {...}}` — entry parameters
2. Interleaved wrap events and LLM spans sorted by timestamp:
   - `{"type": "wrap", "name": "...", "purpose": "input|state|output", "data": ..., "captured_at": "..."}`
   - `{"type": "llm_span_trace", "request_model": "...", ...}`

### Analysis updates

- `pixie analyze` now shows full execution flow in entry details
  (wrap events + LLM calls), not just LLM calls.
- `_load_full_trace()` added for loading all record types.
- `_load_entry_traces()` updated to filter from full trace with
  backward compatibility for old LLM-only trace files.

## Files affected

- `pixie/instrumentation/models.py` — `LLMSpanTrace` subclasses `LLMSpanLog`
- `pixie/instrumentation/wrap.py` — eval input injection now emits
- `pixie/harness/trace_capture.py` — complete rewrite (EntryTraceCollector, EntryTraceLogProcessor)
- `pixie/harness/runner.py` — calls `record_entry_kwargs()`
- `pixie/cli/test_command.py` — uses new collector + log processor API
- `pixie/cli/analyze_command.py` — full trace loading and rendering
- `tests/pixie/harness/test_trace_capture.py` — rewritten (13 tests)
- `tests/pixie/cli/test_analyze_command.py` — added full trace tests
- `tests/manual/datasets/chatbot.json` — NEW chatbot dataset for trace verification

## Migration notes

- Backward compatible — old trace files with only `llm_span_trace` records
  are still loaded correctly by `_load_entry_traces()`.
- Old result.json files without `traceFile` still work (field defaults to `None`).
- The `TraceCaptureHandler` name is preserved as an alias for `EntryTraceCollector`.
