# Test Trace Capture

## What changed

Added always-on LLM trace capture to `pixie test`. Every dataset entry now gets
a per-entry JSONL trace file containing all LLM calls made during that entry's
execution.

### New components

- `TraceCaptureHandler` — an `InstrumentationHandler` subclass that collects
  `LLMSpan` objects keyed by entry index using `contextvars.ContextVar`.
- `LLMSpanTrace` — a Pydantic model for full LLM span records including timing
  and token data.
- `current_entry_index` — a `ContextVar[int | None]` that associates LLM spans
  with the correct dataset entry during concurrent execution.

### Integration

- `pixie test` calls `enable_llm_tracing()` at run start, registers the
  `TraceCaptureHandler`, and writes per-entry trace files after each entry completes.
- `EntryResult` gained an optional `trace_file: str | None` field for the relative
  path to the trace JSONL file.
- `runner.py` sets `current_entry_index` before each entry runs.

### Trace file format

Each line in `{result_dir}/traces/entry-{i}.jsonl` is a JSON record with:
`type`, `operation`, `provider`, `request_model`, `response_model`,
`input_tokens`, `output_tokens`, `duration_ms`, `started_at`, `ended_at`,
`input_messages`, `output_messages`, `tool_definitions`, `finish_reasons`,
`error_type`.

## Files affected

- `pixie/harness/trace_capture.py` — NEW
- `pixie/instrumentation/models.py` — added `LLMSpanTrace` model
- `pixie/harness/run_result.py` — added `trace_file` field, updated serialization
- `pixie/harness/runner.py` — added `entry_index` param, sets context var
- `pixie/cli/test_command.py` — trace capture initialization and per-entry writing
- `tests/pixie/harness/test_trace_capture.py` — NEW (7 tests)
- `tests/pixie/harness/__init__.py` — NEW (empty init)

## Migration notes

- Backward compatible — old `result.json` files without `traceFile` still load
  (field defaults to `None`).
- The `traces/` directory is created inside the result directory alongside
  `result.json`.
- When no OpenInference instrumentors are installed, trace files are still
  created but may be empty (zero lines).
