# Concurrent Evaluator Execution with Rate Limiting

## What Changed

Introduced three levels of concurrency to speed up `pixie test` execution,
plus a central rate limiter to protect LLM evaluator API endpoints.

### Level 1: Concurrent test functions (`runner.py`)

- `run_tests()` now uses a single `asyncio.run()` call with
  `asyncio.gather()` to run all test cases concurrently.
- Async test functions are `await`ed directly inside the shared event loop.
- Sync test functions run via `asyncio.to_thread()` with a thread-local
  event loop (preserving compatibility with sync code that calls
  `asyncio.get_event_loop()`).
- `ScorecardCollector` uses `ContextVar`, so each asyncio Task gets its
  own collector — no cross-test interference.

### Level 2: Concurrent dataset rows (`eval_utils.py`)

- `assert_pass()` now processes all dataset inputs concurrently via
  `asyncio.gather()` instead of a sequential `for` loop.
- Each row still runs its evaluators concurrently (unchanged).
- Extracted `_process_single_input()` helper for a single row's evaluator
  logic.

### Level 3: Rate limiting (`rate_limiter.py`)

- New module `pixie/evals/rate_limiter.py` with:
  - `RateLimitConfig` — frozen dataclass with configurable RPS, RPM, TPS,
    TPM defaults.
  - `EvalRateLimiter` — async-safe rate limiter using sliding windows and
    an `asyncio.Lock`.
  - `configure_rate_limits()` / `get_rate_limiter()` — module-level
    singleton management.
- Integrated into `evaluate()` in `evaluation.py` — each evaluator call
  acquires the rate limiter (when configured) before executing.
- `configure_rate_limits` and `RateLimitConfig` exported from
  `pixie/__init__.py`.

## Files Affected

| File                                     | Change                                                                 |
| ---------------------------------------- | ---------------------------------------------------------------------- |
| `pixie/evals/rate_limiter.py`            | **New** — rate limiter module                                          |
| `pixie/evals/runner.py`                  | Concurrent test execution via `asyncio.gather`                         |
| `pixie/evals/eval_utils.py`              | Concurrent dataset row processing; extracted `_process_single_input()` |
| `pixie/evals/evaluation.py`              | Rate limiter integration in `evaluate()`                               |
| `pixie/__init__.py`                      | Export `RateLimitConfig`, `configure_rate_limits`                      |
| `tests/pixie/evals/test_rate_limiter.py` | **New** — 13 unit tests for rate limiter                               |
| `tests/pixie/evals/test_eval_utils.py`   | Fixed 2 tests for non-deterministic side-effect ordering               |

## Migration Notes

- **No API changes** — existing `pixie test` usage is fully compatible.
- Rate limiting is **opt-in**: no limiter is active by default. Call
  `configure_rate_limits(RateLimitConfig(...))` to enable it.
- Test functions now run concurrently. Tests that relied on sequential
  execution order (rare) may need adjustment.
- Side-effect lists populated inside evaluator callbacks during concurrent
  `assert_pass` runs are no longer guaranteed to be in input order.
