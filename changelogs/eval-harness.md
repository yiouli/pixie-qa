# Evals Harness & Multi-Handler Instrumentation

## What Changed

### New module: `pixie.evals`

Implemented the eval test harness following the spec in `specs/evals-harness.md`.

#### Evaluation Primitives (`pixie/evals/evaluation.py`)

- `Evaluation` frozen dataclass with `score`, `reasoning`, `details`
- `Evaluator` protocol — any async/sync callable matching the signature
- `evaluate()` — runs one evaluator against one evaluable; auto-wraps sync
  callables, clamps scores to [0.0, 1.0], catches evaluator exceptions

#### Higher-Level Utilities (`pixie/evals/eval_utils.py`)

- `run_and_evaluate(runnable, input, evaluator)` — runs the application
  function with trace capture, then evaluates the resulting spans
- `assert_pass(runnable, inputs, evaluators, passes)` — batch evaluation over
  multiple inputs × evaluators with configurable pass criteria
- `EvalAssertionError` — carries the full `[passes][evaluators]` results tensor
- Default pass criteria: all individual scores must be ≥ 0.5

#### In-Memory Trace Capture (`pixie/evals/trace_capture.py`)

- `MemoryTraceHandler` — `InstrumentationHandler` subclass that collects spans
  into an in-memory list; provides `get_trace(trace_id)` and `get_all_traces()`
- `capture_traces()` — async context manager that calls `init()` (no-op if
  already done), registers a `MemoryTraceHandler` via `add_handler()`, and
  removes it on exit after flushing the delivery queue

#### Test Discovery & Runner (`pixie/evals/runner.py`)

- `discover_tests(path, *, filter_pattern=None)` — discovers `test_*` functions
  in `test_*.py` / `*_test.py` files
- `run_tests(cases)` — executes test cases (sync or async) and collects results
- `format_results(results, *, verbose=False)` — human-readable output
- `EvalTestResult` dataclass with `passed` / `failed` / `error` status

#### Package Exports (`pixie/evals/__init__.py`)

Exports: `Evaluation`, `Evaluator`, `evaluate`, `run_and_evaluate`,
`assert_pass`, `EvalAssertionError`, `MemoryTraceHandler`, `capture_traces`

### Instrumentation: Multi-handler support (`pixie.instrumentation`)

The `init()` function no longer accepts a `handler` parameter. OTel setup and
handler registration are now separate concerns:

- **`init(*, capture_content, queue_size)`** — sets up the TracerProvider, span
  processor, delivery queue, and auto-instrumentors. Idempotent — a second call
  is a no-op.
- **`add_handler(handler)`** — registers a handler to receive span
  notifications. Multiple handlers are supported; each receives every span.
- **`remove_handler(handler)`** — unregisters a previously registered handler.

Internally, a new `_HandlerRegistry` (a fan-out `InstrumentationHandler`)
dispatches to all registered handlers with per-handler exception isolation and
a `threading.Lock` for thread safety. A `_reset_state()` helper is available
for test isolation (not part of the public API).

### CLI Entry Point (`pixie/cli/test_command.py`)

- `pixie test` CLI script registered in `pyproject.toml`
- Supports `--filter` / `-k` and `--verbose` / `-v` flags
- Calls `px.init()` before running discovered test functions

## Files Affected

### New files

- `pixie/evals/__init__.py` — package exports
- `pixie/evals/evaluation.py` — evaluation primitives
- `pixie/evals/eval_utils.py` — higher-level utilities
- `pixie/evals/trace_capture.py` — in-memory trace capture
- `pixie/evals/runner.py` — test discovery and runner
- `pixie/cli/__init__.py` — CLI package
- `pixie/cli/test_command.py` — `pixie test` CLI entry point
- `tests/pixie/evals/__init__.py` — test package
- `tests/pixie/evals/test_evaluation.py` — 13 tests
- `tests/pixie/evals/test_eval_utils.py` — 15 tests
- `tests/pixie/evals/test_trace_capture.py` — 10 tests
- `tests/pixie/evals/test_runner.py` — 14 tests

### Modified files

- `pixie/instrumentation/__init__.py` — refactored `init()`, added
  `add_handler()`, `remove_handler()`, `_reset_state()`
- `pixie/instrumentation/handler.py` — added `_HandlerRegistry` class
- `tests/pixie/instrumentation/conftest.py` — added `_reset_instrumentation`
  autouse fixture
- `tests/pixie/instrumentation/test_context.py` — updated `init()` calls
- `tests/pixie/instrumentation/test_integration.py` — updated `init()` calls,
  replaced `TestReinitIdempotent` with `TestMultipleHandlers`
- `pyproject.toml` — added `pixie-test` script entry point
- `README.md` — updated API docs, added evals harness section and CLI docs
- `specs/instrumentation.md` — updated `init()`, added `add_handler` /
  `remove_handler`, updated Global State and test descriptions

## Migration Notes

### Breaking change: `init()` signature

```python
# Before
px.init(MyHandler(), capture_content=True)

# After
px.init(capture_content=True)
px.add_handler(MyHandler())
```

### New: `run_and_evaluate` and `assert_pass` signatures

```python
await run_and_evaluate(
    evaluator=my_metric,
    runnable=my_app,
    input="What is your refund policy?",
)

await assert_pass(
    runnable=my_app,
    inputs=["Q1", "Q2", "Q3"],
    evaluators=[my_metric],
    passes=3,
)
