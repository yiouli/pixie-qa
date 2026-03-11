# Usability Improvements

## What Changed

Implemented a collection of convenience features that make the eval + instrumentation stack usable out of the box with minimal setup code. These are additions to existing modules and thin wrappers that reduce boilerplate.

### 1. Environment Variable Configuration (`pixie/config.py`)

- New `PixieConfig` frozen dataclass with `db_path` and `db_engine` fields.
- New `get_config()` that reads `PIXIE_DB_PATH` / `PIXIE_DB_ENGINE` env vars with sensible defaults.
- Updated `pixie/storage/piccolo_conf.py` to use `get_config()` instead of direct `os.environ` access.

### 2. Pre-Made Storage Handler (`pixie/instrumentation/handlers.py`)

- New `StorageHandler(InstrumentationHandler)` — async handler that persists spans to `ObservationStore`, with exception suppression.
- New `enable_storage()` — zero-parameter convenience function that creates a store with default config, runs table migration, and registers the handler. Idempotent.
- `_reset_storage_handler()` test helper for resetting module state.

### 3. Trace-to-Evaluable Helpers (`pixie/evals/trace_helpers.py`)

- `last_llm_call(trace)` — finds the `LLMSpan` with the latest `ended_at` across the full tree, returns as `LLMSpanEval`.
- `root(trace)` — returns the first root node's span as `Evaluable`.
- Both raise `ValueError` on invalid input (no LLM spans / empty trace).

### 4. Pre-Made Pass Criteria (`pixie/evals/criteria.py`)

- `ScoreThreshold(threshold=0.5, pct=1.0)` — configurable pass criteria with "at least one pass" semantics for multi-pass evaluation.
- Updated `assert_pass()` default `pass_criteria` from inline `_default_pass_criteria` to `ScoreThreshold()`.

### 5. Updated Exports

- `pixie/__init__.py` now re-exports `enable_storage` and `StorageHandler`.
- `pixie/evals/__init__.py` now exports `ScoreThreshold`, `last_llm_call`, and `root`.

## Files Affected

### New Files

- `pixie/config.py` — `PixieConfig`, `get_config()`
- `pixie/instrumentation/handlers.py` — `StorageHandler`, `enable_storage()`
- `pixie/evals/trace_helpers.py` — `last_llm_call()`, `root()`
- `pixie/evals/criteria.py` — `ScoreThreshold`
- `tests/pixie/test_config.py` — config tests
- `tests/pixie/instrumentation/test_storage_handler.py` — handler tests
- `tests/pixie/evals/test_trace_helpers.py` — trace helper tests
- `tests/pixie/evals/test_criteria.py` — criteria tests

### Modified Files

- `pixie/storage/piccolo_conf.py` — uses `get_config()` instead of `os.environ`
- `pixie/evals/eval_utils.py` — default `pass_criteria` now uses `ScoreThreshold()`
- `pixie/evals/__init__.py` — exports new symbols
- `pixie/__init__.py` — re-exports `enable_storage`, `StorageHandler`
- `README.md` — documents new features, config table, usage examples
- `changelogs/usability-utils.md` — this file

## Migration Notes

- `assert_pass()` default pass criteria changed from "all individual scores >= 0.5" to `ScoreThreshold()` which checks "all inputs must have all evaluators >= 0.5". Semantically equivalent for single-pass, single-evaluator usage. Multi-evaluator usage is now per-input rather than global — an input passes only if _all_ its evaluators score >= threshold.
- `piccolo_conf.py` now reads `PIXIE_DB_PATH` via `get_config()` instead of directly from `os.environ`. Behavior is identical for existing users.
