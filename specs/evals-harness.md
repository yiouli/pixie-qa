# Eval Test Harness — Implementation Spec

> **Note:** The `expected_output` / `expected_outputs` parameters described in the
> evaluation function signatures have been superseded by `specs/dataset-management.md`.
> `expected_output` is now embedded directly in the `Evaluable` model. Evaluators read
> `evaluable.expected_output` instead of receiving it as a kwarg.

## Overview

A pytest-style test discovery and runner for LLM application evaluation. Users define test functions, run them via `pixie test`, and use framework-provided `evaluate` / `assert_pass` functions instead of `assert` statements. The runner sets up in-memory trace capture automatically, so evaluators have access to full execution traces without any production instrumentation dependency.

This module has four concerns:

1. **Evaluation primitives** — `Evaluation` result, `Evaluator` protocol, `evaluate` function
2. **Higher-level eval utilities** — `run_and_evaluate`, `assert_pass`
3. **Test discovery and runner** — `pixie test` CLI that discovers and runs eval test functions
4. **In-memory trace capture** — automatic trace handler setup during test execution

Imports from the observation store module: `Evaluable`, `ObserveSpanEval`, `LLMSpanEval`, `as_evaluable`, `ObservationNode`, `build_tree`.

Imports from the instrumentation module: `ObserveSpan`, `LLMSpan`, and the span handler/processor registration API.

---

## 1. Evaluation Primitives

### File: `evaluation.py`

#### `Evaluation`

The result of a single evaluator applied to a single test case.

```python
@dataclass(frozen=True)
class Evaluation:
    score: float          # 0.0 to 1.0
    reasoning: str        # human-readable explanation
    details: dict = field(default_factory=dict)  # arbitrary JSON-serializable metadata
```

`score` must be clamped to [0.0, 1.0]. If an evaluator returns a value outside this range, the framework should clamp it and log a warning.

`reasoning` is required — every evaluation must explain itself. This is a lesson from DeepEval's design where `reason` is the most praised feature.

`details` is optional and freeform. Useful for LLM-as-judge evaluators to include the raw judge response, token usage, or intermediate reasoning steps.

#### `Evaluator` Protocol

```python
class Evaluator(Protocol):
    async def __call__(
        self,
        evaluable: Evaluable,
        *,
        trace: list[ObservationNode] | None = None,
    ) -> Evaluation: ...
```

**Design rationale:**

- **`evaluable: Evaluable`** — the uniform interface from the observation store module. Evaluators access `eval_input`, `eval_output`, `eval_metadata` without knowing whether the underlying span is `ObserveSpan` or `LLMSpan`.
- **`trace: list[ObservationNode] | None`** — the full trace tree, optional. Most evaluators only need the evaluable's input/output. Trace-aware evaluators (e.g., "did the agent call the right tools in the right order?") can traverse the tree, use `find()` / `find_by_type()`, or serialize it with `to_text()` for LLM-as-judge.
- **Async** — evaluators are async by default. Sync evaluators are supported: the framework wraps sync callables in `asyncio.to_thread` at call time (see section 3). This avoids DeepEval's `measure()` / `a_measure()` duplication problem.
- **Callable protocol** — evaluators are any async callable matching this signature. Plain async functions, class instances with `__call__`, or closures all work. No base class inheritance required.

**A plain function satisfies this protocol:**

```python
async def exact_match(evaluable: Evaluable, *, trace=None) -> Evaluation:
    match = str(evaluable.eval_output).strip().lower() == "expected"
    return Evaluation(
        score=1.0 if match else 0.0,
        reasoning="Exact match" if match else "No match",
    )
```

**A class instance satisfies this protocol:**

```python
class LLMJudge:
    def __init__(self, criteria: str, model: str = "gpt-4o"):
        self.criteria = criteria
        self.model = model

    async def __call__(self, evaluable, *, trace=None):
        prompt = f"Evaluate: {evaluable.eval_output}\nCriteria: {self.criteria}"
        result = await call_llm(self.model, prompt)
        return Evaluation(score=result.score, reasoning=result.reasoning)
```

**A sync function also works** (the framework handles wrapping):

```python
def length_check(evaluable: Evaluable, *, trace=None) -> Evaluation:
    output = str(evaluable.eval_output)
    ok = len(output) < 500
    return Evaluation(score=1.0 if ok else 0.0, reasoning=f"Length: {len(output)}")
```

#### `evaluate`

The base evaluation function. Runs a single evaluator against a single evaluable with an optional trace.

```python
async def evaluate(
    evaluator: Evaluator,
    evaluable: Evaluable,
    *,
    expected_output: Any = None,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
```

**Behavior:**

1. If `evaluator` is a sync callable (not a coroutine function), wrap it with `asyncio.to_thread`.
2. Call the evaluator with `evaluable` and `trace`. If `expected_output` is not `None`, also pass it as a keyword argument.
3. Validate the returned `Evaluation`: clamp `score` to [0.0, 1.0], ensure `reasoning` is a non-empty string.
4. If the evaluator raises an exception, **let it propagate** to the caller. Evaluator errors (missing API keys, network failures, etc.) must never be silently converted to a zero score.
5. Return the `Evaluation`.

---

## 2. Higher-Level Eval Utilities

### File: `eval_utils.py`

#### `run_and_evaluate`

Runs a user-provided callable while capturing traces, then evaluates the result.

```python
async def run_and_evaluate(
    evaluator: Evaluator,
    runnable: Callable,
    input: Any,
    *,
    expected_output: Any = None,
    from_trace: Callable[[list[ObservationNode]], Evaluable] | None = None,
) -> Evaluation:
```

**Behavior:**

1. Set up an in-memory trace handler (see section 4) scoped to this call.
2. Call `runnable(input)`. If `runnable` is async, await it. If sync, run via `asyncio.to_thread`.
3. After `runnable` completes, collect all captured spans from the in-memory handler.
4. Build the trace tree via `build_tree(spans)`.
5. Determine the evaluable:
   - If `from_trace` is provided, call `from_trace(trace_tree)` to get the `Evaluable`. This lets the user select a specific span for evaluation (e.g., the last LLM call, a specific component by name).
   - If `from_trace` is None, use the root observation span. Wrap it with `as_evaluable()`.
6. Call `evaluate(evaluator, evaluable, expected_output=expected_output, trace=trace_tree)`.
7. Tear down the in-memory trace handler.
8. Return the `Evaluation`.

**Example usage:**

```python
# Evaluate root span output
result = await run_and_evaluate(
    evaluator=my_metric,
    runnable=my_rag_app,
    input="What is our refund policy?",
)

# Evaluate a specific component
result = await run_and_evaluate(
    evaluator=faithfulness_metric,
    runnable=my_rag_app,
    input="What is our refund policy?",
    from_trace=lambda tree: as_evaluable(tree[0].find("generator")[0].span),
)
```

#### `assert_pass`

Runs a collection of test cases against a collection of evaluators over multiple passes, then applies a pass criteria function to determine pass/fail.

```python
async def assert_pass(
    runnable: Callable,
    inputs: list[Any],
    evaluators: list[Evaluator],
    *,
    expected_outputs: list[Any] | None = None,
    passes: int = 1,
    pass_criteria: Callable[[list[list[list[Evaluation]]]], tuple[bool, str]] | None = None,
    from_trace: Callable[[list[ObservationNode]], Evaluable] | None = None,
) -> None:
```

**Parameters:**

- `runnable` — the application function to test.
- `inputs` — list of inputs, each passed to `runnable`.
- `evaluators` — list of evaluators to run against each input's result.
- `expected_outputs` — optional list of expected values, one per input. Must have the same length as `inputs` when provided. Each value is forwarded as `expected_output` to `run_and_evaluate`.
- `passes` — how many times to run the entire test matrix. Useful for non-deterministic LLM outputs where you want statistical confidence. Default 1.
- `pass_criteria` — a function that receives the full results tensor and returns `(passed: bool, message: str)`. If None, use the default criteria (see below).
- `from_trace` — optional span selector, passed through to `run_and_evaluate`.

**The results tensor:**

`list[list[list[Evaluation]]]` with shape `[passes][inputs][evaluators]`.

- `results[p][i][e]` is the `Evaluation` from pass `p`, input `i`, evaluator `e`.

**Execution:**

1. For each pass `p` in `range(passes)`:
   - For each input `i` in `inputs`:
     - Call `run_and_evaluate(evaluator, runnable, input, from_trace=from_trace)` for each evaluator.
     - Collect the `Evaluation` results.
2. Assemble the results tensor.
3. Call `pass_criteria(results)` to get `(passed, message)`.
4. If `passed` is False, raise `EvalAssertionError(message, results=results)`.
5. If `passed` is True, return normally.

**Concurrency:** Within a single pass, inputs should be run sequentially (to avoid shared state issues in the runnable). Evaluators for a single input may be run concurrently via `asyncio.gather`. Different passes are run sequentially.

**Default pass criteria:**

If `pass_criteria` is None, use:

```python
def default_pass_criteria(results):
    all_scores = [e.score for pass_ in results for input_ in pass_ for e in input_]
    avg = sum(all_scores) / len(all_scores) if all_scores else 0.0
    passed = all(s >= 0.5 for s in all_scores)
    return (passed, f"Average score: {avg:.2f}, all >= 0.5: {passed}")
```

Every individual evaluation must score >= 0.5. This is deliberately strict — users who want different criteria should provide their own `pass_criteria`.

#### `EvalAssertionError`

```python
class EvalAssertionError(AssertionError):
    def __init__(self, message: str, results: list[list[list[Evaluation]]]):
        super().__init__(message)
        self.results = results
```

Carries the full results tensor so the runner can produce detailed failure reports.

---

## 3. Test Discovery and Runner

### File: `runner.py`

#### Test discovery

The `pixie test` command discovers eval test functions using the following rules:

1. Search for Python files matching `test_*.py` or `*_test.py` in the target directory (default: current directory). Recursive.
2. Within each file, find functions whose names start with `test_`.
3. Test functions may be sync or async. The runner handles both.
4. Test functions take no arguments (like pytest test functions without fixtures).
5. **Import errors are loud**: If a test file fails to import (syntax errors, missing dependencies, bad imports), the error propagates immediately rather than silently skipping the file and reporting "no tests collected".

**Example test file:**

```python
# test_my_app.py
from pixie.eval import evaluate, run_and_evaluate, assert_pass, Evaluation, Evaluable

async def my_metric(evaluable: Evaluable, *, trace=None) -> Evaluation:
    output = str(evaluable.eval_output)
    return Evaluation(
        score=1.0 if "refund" in output.lower() else 0.0,
        reasoning="Contains refund info" if "refund" in output.lower() else "Missing refund info",
    )

async def test_single_case():
    result = await run_and_evaluate(
        evaluator=my_metric,
        runnable=my_rag_app,
        input="What is your refund policy?",
    )
    # User can inspect result, or just let assert_pass handle pass/fail

async def test_batch():
    await assert_pass(
        runnable=my_rag_app,
        inputs=[
            "What is your refund policy?",
            "How do I reset my password?",
            "What are your business hours?",
        ],
        evaluators=[my_metric],
        passes=3,
    )
```

#### CLI interface

```
pixie test [path] [options]
```

**Arguments:**

- `path` — file or directory to search for tests. Default: current directory.

**Options:**

- `--filter` / `-k` — only run tests whose names contain this substring. Matches against `filename::function_name`.
- `--verbose` / `-v` — show detailed evaluation results (scores, reasoning) for each test case, not just pass/fail.
- `--concurrency` / `-c` — max concurrent test functions. Default: 1 (sequential). Test functions themselves may have internal concurrency, but inter-test concurrency is controlled here.

#### Runner behavior

For each discovered test function:

1. Print the test name.
2. Set up an in-memory trace handler (see section 4) scoped to this test function.
3. Run the test function. If async, run via `asyncio.run` or the existing event loop. If sync, call directly.
4. Catch outcomes:
   - **Pass**: function returns normally. Print green checkmark + test name.
   - **Fail (EvalAssertionError)**: Print red X + test name + the error message (always visible). In verbose mode, also print the full results tensor with per-evaluator scores and reasoning.
   - **Error (other exception)**: Print red X + test name + error summary (always visible). In verbose mode, also print the full traceback.
5. Tear down the in-memory trace handler.
6. After all tests, print summary: `X passed, Y failed, Z errors`.

**Exit code:** 0 if all tests pass, 1 if any test fails or errors.

#### HTML Scorecard

After all tests complete, the runner generates a self-contained HTML scorecard
and saves it to `{config.root}/scorecards/<YYYYMMDD-HHMMSS-normalized-args>.html`.

**Data flow:**

1. Before each test function, the runner activates a `ScorecardCollector`
   (context-var based). While active, every `assert_pass` /
   `assert_dataset_pass` call pushes an `AssertRecord` to the collector.
2. After the test function returns (or raises), the runner drains the
   collector and attaches the records to the `EvalTestResult`.
3. After all tests, the CLI builds a `ScorecardReport` from the enriched
   results, generates HTML via `generate_scorecard_html()`, and writes it
   to disk via `save_scorecard()`.
4. The CLI prints the path: `See <path> for test details`.

**Scorecard contents:**

- **Test run overview** — command args, timestamp, X/N passed summary, and a
  table of all tests with status badges.
- **Per-test detail** — for each test function:
  - Each `assert_pass` / `assert_dataset_pass` call becomes an
    "Assertion #N" card showing:
    - Scoring strategy description (derived from the pass criteria).
    - Per-evaluator pass rate summary table (X/N passed).
    - Input × evaluator score grid with hover tooltips.
  - Multi-pass runs get a tabbed view (one tab per pass).

**Key types** (in `pixie/evals/scorecard.py`):

- `AssertRecord` — frozen dataclass: evaluator names, input labels,
  results tensor, passed flag, criteria message, scoring strategy.
- `TestRecord` — mutable dataclass: test name, status, message, list of
  `AssertRecord`s.
- `ScorecardReport` — command args, list of `TestRecord`s, timestamp.
- `ScorecardCollector` — thread-safe accumulator with
  `activate()` / `deactivate()` / `record()` / `drain()`.

#### Output format

**Normal mode:**

```
pixie test
==================== test session starts ====================

test_my_app.py::test_single_case ✓
test_my_app.py::test_batch ✗
  EvalAssertionError: Average score: 0.44, all >= 0.5: False

==================== 1 passed, 1 failed ====================
```

**Verbose mode (`-v`):**

```
pixie test -v
==================== test session starts ====================

test_my_app.py::test_single_case ✓
  run_and_evaluate: score=0.85, reasoning="Contains refund info"

test_my_app.py::test_batch ✗
  Pass 1:
    Input 0 ("What is your refund policy?"):
      my_metric: 0.90 — "Contains refund info"
    Input 1 ("How do I reset my password?"):
      my_metric: 0.10 — "Missing refund info"
    Input 2 ("What are your business hours?"):
      my_metric: 0.30 — "Missing refund info"
  Pass 2:
    ...
  EvalAssertionError: Average score: 0.44, all >= 0.5: False

==================== 1 passed, 1 failed ====================
```

---

## 4. In-Memory Trace Capture

### File: `trace_capture.py`

The runner needs to capture spans produced during test execution without writing to disk. This is implemented as an in-memory span handler that collects spans into a list.

#### `MemoryTraceHandler`

```python
class MemoryTraceHandler:
    """Collects ObserveSpan and LLMSpan instances into an in-memory list."""

    def __init__(self):
        self.spans: list[ObserveSpan | LLMSpan] = []

    def handle(self, span: ObserveSpan | LLMSpan) -> None:
        """Called by the instrumentation layer when a span completes."""
        self.spans.append(span)

    def get_trace(self, trace_id: str) -> list[ObservationNode]:
        """Filter spans by trace_id and build the tree."""
        matching = [s for s in self.spans if s.trace_id == trace_id]
        return build_tree(matching)

    def get_all_traces(self) -> dict[str, list[ObservationNode]]:
        """Group all captured spans by trace_id and build trees."""
        by_trace: dict[str, list] = {}
        for s in self.spans:
            by_trace.setdefault(s.trace_id, []).append(s)
        return {tid: build_tree(spans) for tid, spans in by_trace.items()}

    def clear(self) -> None:
        self.spans.clear()
```

**Integration with the instrumentation module:**

The instrumentation module has a span handler/processor registration API. The `MemoryTraceHandler.handle` method must conform to the handler interface expected by that API. The runner registers the handler before each test function and deregisters it after.

The exact registration mechanism depends on the instrumentation module's API. The spec assumes something like:

```python
from pixie.instrumentation import register_handler, unregister_handler

handler = MemoryTraceHandler()
register_handler(handler)
# ... run test ...
unregister_handler(handler)
```

If the instrumentation module uses a different pattern (e.g., a context manager, a global list, or an OTel SpanProcessor), adapt accordingly. The key requirement is: spans produced during the test function's execution are captured by this handler, and the handler is isolated per-test (does not leak spans between tests).

#### Context manager for convenience

```python
@contextmanager
def capture_traces():
    """Context manager that installs a MemoryTraceHandler and yields it."""
    handler = MemoryTraceHandler()
    register_handler(handler)
    try:
        yield handler
    finally:
        unregister_handler(handler)
```

This is used internally by `run_and_evaluate` and by the test runner. It can also be used directly in test functions for manual trace inspection:

```python
async def test_trace_inspection():
    with capture_traces() as handler:
        my_app("some input")
        traces = handler.get_all_traces()
        # inspect traces manually
```

---

## 5. Tests

### `tests/test_evaluation.py`

- `Evaluation` clamps score to [0.0, 1.0] on construction (or via `evaluate`).
- `evaluate` with a sync evaluator wraps it and returns correctly.
- `evaluate` with an async evaluator returns correctly.
- `evaluate` propagates exceptions from evaluators (never silently returns score=0.0).
- `evaluate` clamps scores > 1.0 to 1.0 and < 0.0 to 0.0.
- A plain async function satisfies the `Evaluator` protocol.
- A class with async `__call__` satisfies the `Evaluator` protocol.

### `tests/test_eval_utils.py`

- `run_and_evaluate` captures trace and passes it to evaluator.
- `run_and_evaluate` with sync runnable works correctly.
- `run_and_evaluate` with async runnable works correctly.
- `run_and_evaluate` with `from_trace=None` evaluates the root span.
- `run_and_evaluate` with `from_trace` selector evaluates the selected span.
- `run_and_evaluate` produces correct trace tree accessible to evaluator.
- `assert_pass` passes when all evaluations score >= 0.5.
- `assert_pass` raises `EvalAssertionError` when any evaluation scores < 0.5.
- `assert_pass` with `passes=3` runs the full matrix 3 times.
- `assert_pass` results tensor has correct shape `[passes][inputs][evaluators]`.
- `assert_pass` with custom `pass_criteria` uses the provided function.
- `assert_pass` with custom `from_trace` passes it through to `run_and_evaluate`.
- `EvalAssertionError` carries the results tensor.

### `tests/test_runner.py`

- Discovery finds `test_*.py` files recursively.
- Discovery finds functions starting with `test_` in those files.
- Discovery ignores non-test functions.
- Runner executes async test functions.
- Runner executes sync test functions.
- Runner reports pass for functions that return normally.
- Runner reports fail for functions that raise `EvalAssertionError`.
- Runner reports error for functions that raise other exceptions.
- Runner `--filter` flag filters tests by name.
- Runner exit code is 0 when all pass, 1 when any fail.
- Discovery raises `ImportError` when a test file cannot be imported.
- Discovery raises `SyntaxError` when a test file has syntax errors.
- Format always shows error messages (not just in verbose mode).
- In-memory trace handler is installed before each test and removed after.
- Spans from one test do not leak into another test.

### `tests/test_trace_capture.py`

- `MemoryTraceHandler` collects spans via `handle()`.
- `get_trace(trace_id)` returns correct tree for matching spans.
- `get_trace(trace_id)` returns empty list for non-matching trace_id.
- `get_all_traces()` groups spans by trace_id correctly.
- `clear()` removes all collected spans.
- `capture_traces()` context manager registers and unregisters handler.
- Spans produced inside the context manager are captured.
- Spans produced outside the context manager are not captured.

---

## 6. File Structure

```text
pixie/
├── eval/
│   ├── __init__.py          # exports Evaluation, Evaluator, evaluate,
│   │                        #   run_and_evaluate, assert_pass,
│   │                        #   EvalAssertionError, capture_traces,
│   │                        #   ScorecardCollector, ScorecardReport,
│   │                        #   generate_scorecard_html, save_scorecard
│   ├── evaluation.py        # Evaluation, Evaluator protocol, evaluate()
│   ├── eval_utils.py        # run_and_evaluate, assert_pass, EvalAssertionError
│   ├── runner.py            # test discovery, CLI runner
│   ├── scorecard.py         # AssertRecord, TestRecord, ScorecardReport,
│   │                        #   ScorecardCollector, HTML generation,
│   │                        #   save_scorecard()
│   └── trace_capture.py     # MemoryTraceHandler, capture_traces
├── cli/
│   └── test_command.py      # `pixie test` CLI entry point
└── tests/
    └── eval/
        ├── test_evaluation.py
        ├── test_eval_utils.py
        ├── test_runner.py
        ├── test_scorecard.py
        └── test_trace_capture.py
```

---

## 7. Dependencies

- Imports from observation store module: `Evaluable`, `ObserveSpanEval`, `LLMSpanEval`, `as_evaluable`, `ObservationNode`, `build_tree`
- Imports from instrumentation module: `ObserveSpan`, `LLMSpan`, handler registration API
- Python ≥ 3.11
- No new external dependencies. The CLI uses `argparse` from the standard library. Test discovery uses `importlib` and `inspect` from the standard library.

---

## 8. Non-Goals

- **Built-in metric library** — this module provides the primitives (`Evaluator` protocol, `evaluate` function). Pre-built evaluators (faithfulness, relevancy, etc.) are a separate concern. Users write their own or wrap third-party libraries.
- **Dataset management** — `assert_pass` takes a plain `list[Any]` of inputs. Dataset loading, versioning, and storage are separate.
- **Persistent result storage** — evaluation results are printed to console and carried in `EvalAssertionError`. Persisting results to the observation store or a separate results table is a future concern.
- **Parallel test execution** — tests run sequentially by default. `--concurrency` flag allows inter-test parallelism but is not required for the initial implementation.
- **Fixtures / dependency injection** — unlike pytest, test functions take no arguments. Trace capture is handled automatically by the runner. Test setup/teardown is the user's responsibility (use module-level code or helper functions).
- **Plugin system** — no plugin hooks, reporter plugins, or evaluator registries. Keep it simple.
