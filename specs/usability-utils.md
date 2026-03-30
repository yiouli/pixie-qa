# Usability Improvements — Implementation Spec

## Overview

A collection of convenience features that make the eval + instrumentation stack usable out of the box with minimal setup code. These are not new modules — they are additions to existing modules or thin wrappers that reduce boilerplate.

---

## 1. Environment Variable Configuration

### File: `pixie/config.py`

Centralized configuration with env var overrides and sensible defaults.

```python
@dataclass(frozen=True)
class RateLimitConfig:
    rps: float = 4.0
    rpm: float = 50.0
    tps: float = 10_000.0
    tpm: float = 500_000.0


@dataclass(frozen=True)
class PixieConfig:
    root: str                            # PIXIE_ROOT, default "pixie_qa"
    db_path: str                         # PIXIE_DB_PATH, default "pixie_qa/observations.db"
    db_engine: str                       # PIXIE_DB_ENGINE, default "sqlite"
    dataset_dir: str                     # PIXIE_DATASET_DIR, default "pixie_qa/datasets"
    rate_limits: RateLimitConfig | None  # PIXIE_RATE_LIMIT_*, disabled by default
```

```python
def get_config() -> PixieConfig:
    """Read config from environment variables with defaults."""
```

All env vars are prefixed with `PIXIE_`. `get_config()` also loads the nearest `.env` from the current working directory at call time without overriding values already present in `os.environ`, so tests can manipulate `os.environ` before calling `get_config()`.

### Update: `pixie/observation_store/piccolo_conf.py`

Replace the hardcoded path with:

```python
from pixie.config import get_config

config = get_config()
DB = SQLiteEngine(path=config.db_path)
```

---

## 2. Pre-Made Storage Handler

### File: `pixie/instrumentation/handlers.py`

#### `StorageHandler`

A span handler that writes completed spans to the Piccolo-backed `ObservationStore`.
Extends `InstrumentationHandler` and implements both handler methods as async coroutines,
awaiting `store.save()` directly — no bridging or background threads required.

```python
class StorageHandler(InstrumentationHandler):
    def __init__(self, store: ObservationStore):
        self.store = store

    async def on_llm(self, span: LLMSpan) -> None:
        """Persist an LLM span to the observation store."""
        try:
            await self.store.save(span)
        except Exception:
            pass  # log and continue; must not raise

    async def on_observe(self, span: ObserveSpan) -> None:
        """Persist an observe span to the observation store."""
        try:
            await self.store.save(span)
        except Exception:
            pass  # log and continue; must not raise
```

Because the handler is an async coroutine, `store.save()` is awaited naturally inside the
dedicated asyncio event loop managed by `_DeliveryQueue`. No internal queue, background
thread, or `asyncio.run_coroutine_threadsafe` bridge is needed.

#### `enable_storage()`

Zero-parameter convenience function that creates a `StorageHandler` with default config and registers it with the instrumentation layer.

```python
def enable_storage() -> StorageHandler:
    """Set up Piccolo storage with default config and register the handler.

    Creates the observation table if it doesn't exist.
    Returns the handler for optional manual control (e.g., flushing).
    """
```

**Behavior:**

1. Call `get_config()` to get database path.
2. Create `ObservationStore` with the configured engine.
3. Run table creation migration if table doesn't exist (Piccolo's `create_table` or migration).
4. Create `StorageHandler(store)`.
5. Register it with the instrumentation layer via `register_handler(handler)`.
6. Return the handler.

**Usage:**

```python
from pixie import enable_storage

enable_storage()  # one line, everything works

# Now any instrumented code automatically persists traces
```

---

## 3. Pre-Made Trace → Evaluable Helpers

### File: `pixie/evals/trace_helpers.py`

Convenience functions that extract an `Evaluable` from a trace tree. These are `from_trace` callables for use with `run_and_evaluate` and `assert_pass`.

#### `last_llm_call`

```python
def last_llm_call(trace: list[ObservationNode]) -> Evaluable:
    """Find the LLMSpan with the latest ended_at in the trace tree, wrap as Evaluable.

    Raises ValueError if no LLMSpan exists in the trace.
    """
```

**Algorithm:**

1. Flatten all nodes in the trace tree (recursive traversal).
2. Filter to nodes where `isinstance(node.span, LLMSpan)`.
3. Sort by `node.span.ended_at` descending.
4. Take the first one.
5. Return `LLMSpanEval(node.span)`.

#### `root`

```python
def root(trace: list[ObservationNode]) -> Evaluable:
    """Return the first root node's span as Evaluable.

    Raises ValueError if trace is empty.
    """
```

**Algorithm:**

1. Take `trace[0]` (the first root node).
2. Return `as_evaluable(trace[0].span)`.

#### Usage with `run_and_evaluate` and `assert_pass`

```python
from pixie.eval import run_and_evaluate, assert_pass
from pixie.eval.trace_helpers import last_llm_call, root

# Evaluate the last LLM call
result = await run_and_evaluate(
    evaluator=my_metric,
    runnable=my_app,
    input="hello",
    from_trace=last_llm_call,
)

# Evaluate root span
result = await run_and_evaluate(
    evaluator=my_metric,
    runnable=my_app,
    input="hello",
    from_trace=root,
)

# In assert_pass
await assert_pass(
    runnable=my_app,
    inputs=["q1", "q2"],
    evaluators=[my_metric],
    from_trace=last_llm_call,
)
```

---

## 4. Pre-Made Pass Criteria

### File: `pixie/evals/criteria.py`

#### `ScoreThreshold`

A configurable pass criteria for `assert_pass`.

```python
@dataclass
class ScoreThreshold:
    threshold: float = 0.5
    pct: float = 1.0  # 0.0 to 1.0, fraction of test cases that must pass

    def __call__(
        self, results: list[list[list[Evaluation]]]
    ) -> tuple[bool, str]:
```

**Semantics:** For **at least one pass**, `pct` fraction of all test cases must score >= `threshold` for **all evaluators** in that test case.

**Algorithm:**

```text
for each pass p:
    passing_inputs = 0
    total_inputs = len(results[p])
    for each input i:
        all_evals_pass = all(e.score >= threshold for e in results[p][i])
        if all_evals_pass:
            passing_inputs += 1
    if passing_inputs / total_inputs >= pct:
        return (True, message)
return (False, message)
```

The "at least one pass" semantics means: when running multiple passes over non-deterministic LLM outputs, the test passes if any single pass meets the criteria. This is useful for catching "can the system ever produce good output" vs. "does the system always produce good output."

**Message format:**

On pass:

```text
Pass (pass 2/3): 8/10 inputs (80.0%) scored >= 0.5 on all evaluators (required: 70.0%)
```

On fail:

```text
Fail: best pass was 2/3 with 5/10 inputs (50.0%) scoring >= 0.5 on all evaluators (required: 70.0%)
```

**Examples:**

```python
from pixie.eval.criteria import ScoreThreshold

# All test cases must score >= 0.5 on all evaluators (default)
await assert_pass(..., pass_criteria=ScoreThreshold())

# 80% of test cases must score >= 0.7
await assert_pass(..., pass_criteria=ScoreThreshold(threshold=0.7, pct=0.8))

# At least one test case must score perfectly (useful for "can it ever get this right?")
await assert_pass(
    ...,
    pass_criteria=ScoreThreshold(threshold=1.0, pct=0.1),  # 10% need perfect score
    passes=5,  # run 5 times to give it a chance
)
```

#### Update default in `assert_pass`

Change the default `pass_criteria` in `assert_pass` from the inline default function to `ScoreThreshold()`:

```python
async def assert_pass(
    ...
    pass_criteria: Callable[..., tuple[bool, str]] | None = None,
    ...
) -> None:
    if pass_criteria is None:
        pass_criteria = ScoreThreshold()
    ...
```

---

## 5. Tests

### `tests/test_config.py`

- `get_config()` returns defaults when no env vars are set.
- `get_config()` reads `PIXIE_DB_PATH` when set.
- `get_config()` reads `PIXIE_DB_ENGINE` when set.
- `get_config()` returns `rate_limits=None` when rate limiting is not enabled.
- `get_config()` builds `rate_limits` from `PIXIE_RATE_LIMIT_ENABLED` and `PIXIE_RATE_LIMIT_*`.
- `get_config()` loads `PIXIE_RATE_LIMIT_*` values from `.env`.

### `tests/test_storage_handler.py`

- `StorageHandler.on_observe()` awaits `store.save()` with the given `ObserveSpan`.
- `StorageHandler.on_llm()` awaits `store.save()` with the given `LLMSpan`.
- `StorageHandler.on_observe()` does not raise when `store.save()` raises (exception swallowed).
- `enable_storage()` creates table and registers handler.
- `enable_storage()` is idempotent (calling twice doesn't duplicate handlers).

### `tests/test_trace_helpers.py`

- `last_llm_call` returns the `LLMSpan` with the latest `ended_at`, wrapped as `LLMSpanEval`.
- `last_llm_call` raises `ValueError` when no `LLMSpan` exists.
- `last_llm_call` works with multi-level nested traces.
- `root` returns the first root node's span wrapped as `Evaluable`.
- `root` raises `ValueError` on empty trace.

### `tests/test_criteria.py`

- `ScoreThreshold()` with default params: all scores >= 0.5 → passes.
- `ScoreThreshold()` with one score < 0.5 → fails.
- `ScoreThreshold(threshold=0.7)`: scores between 0.5 and 0.7 → fails.
- `ScoreThreshold(pct=0.8)`: 80% of inputs pass → passes.
- `ScoreThreshold(pct=0.8)`: 70% of inputs pass → fails.
- Multiple passes: first pass fails, second pass meets criteria → overall passes.
- Multiple passes: no pass meets criteria → fails, message reports best pass.
- Message format includes pass number, input counts, and percentage.

---

## 6. File Structure (additions/changes)

```text
pixie/
├── config.py                              # NEW: PixieConfig, get_config()
├── __init__.py                            # UPDATE: re-export enable_storage, observe
├── instrumentation/
│   ├── observe.py                         # NEW: @observe decorator, observation() cm, SpanBuilder
│   └── handlers.py                        # NEW: StorageHandler, enable_storage()
├── evals/
│   ├── trace_helpers.py                   # NEW: last_llm_call, root
│   ├── criteria.py                        # NEW: ScoreThreshold
│   └── eval_utils.py                      # UPDATE: default pass_criteria uses ScoreThreshold()
├── storage/
│   └── piccolo_conf.py                    # UPDATE: uses get_config()
└── tests/
    ├── test_config.py
    ├── test_storage_handler.py
    ├── test_trace_helpers.py
    └── test_criteria.py
```
