# Dataset Management — Changelog

## What Changed

### Evaluable Refactoring

Replaced the `Evaluable` Protocol in `pixie/storage/evaluable.py` with a **Pydantic `BaseModel`**.
The new `Evaluable` is a frozen model with JSON-compatible fields:

- `eval_input` (`JsonValue`) — input to the observed operation
- `eval_output` (`JsonValue`) — output of the observed operation
- `eval_metadata` (`dict[str, JsonValue] | None`) — supplementary metadata
- `expected_output` (`JsonValue | _Unset`) — expected reference output, defaults to `UNSET` sentinel

The `_Unset` enum sentinel distinguishes "expected output was never set" from "expected output is explicitly `None`".

**Removed classes**: `ObserveSpanEval` and `LLMSpanEval` adapter classes. The `as_evaluable()` factory now returns `Evaluable` model instances directly.

**Removed parameters**: `expected_output` / `expected_outputs` parameters removed from `evaluate()`, `run_and_evaluate()`, `assert_pass()`, and `AutoevalsAdapter.__call__()`. Evaluators now read `evaluable.expected_output` directly.

**New parameter**: `assert_pass()` gains an `evaluables: list[Evaluable] | None` parameter. When provided, evaluables are used directly (each carries its own `expected_output`).

### Dataset Storage

New `pixie/dataset/` package for managing named collections of `Evaluable` items:

- `Dataset` — Pydantic model with `name` and `items` (tuple of `Evaluable`)
- `DatasetStore` — JSON-file-backed CRUD:
  - `create(name, items?)` — create new dataset
  - `get(name)` — load by name
  - `list()` — list all dataset names
  - `delete(name)` — delete dataset
  - `append(name, *items)` — add items
  - `remove(name, index)` — remove item by index

### Configuration

Added `dataset_dir` field to `PixieConfig` with `PIXIE_DATASET_DIR` env var (default: `"pixie_datasets"`).

### Dependencies

Added `pydantic>=2.0` as a runtime dependency.

## Files Affected

### Source

| File | Change |
|------|--------|
| `pixie/storage/evaluable.py` | Protocol → Pydantic BaseModel; added `_Unset`, `UNSET`, `expected_output`; removed adapter classes |
| `pixie/storage/__init__.py` | Removed `ObserveSpanEval`, `LLMSpanEval`; added `UNSET` |
| `pixie/config.py` | Added `dataset_dir` field and `PIXIE_DATASET_DIR` |
| `pixie/evals/evaluation.py` | Removed `expected_output` from `Evaluator` and `evaluate()` |
| `pixie/evals/eval_utils.py` | Removed `expected_output`/`expected_outputs`; added `evaluables` to `assert_pass()` |
| `pixie/evals/scorers.py` | Updated `AutoevalsAdapter` to read from `evaluable.expected_output` |
| `pixie/evals/trace_helpers.py` | Uses `as_evaluable()` instead of adapter classes |
| `pixie/dataset/__init__.py` | New — public API exports |
| `pixie/dataset/models.py` | New — `Dataset` model |
| `pixie/dataset/store.py` | New — `DatasetStore` CRUD |
| `pyproject.toml` | Added `pydantic>=2.0` dependency |

### Tests

| File | Change |
|------|--------|
| `tests/pixie/observation_store/test_evaluable.py` | Rewritten for Pydantic model |
| `tests/pixie/evals/test_evaluation.py` | Removed `expected_output` param usage |
| `tests/pixie/evals/test_eval_utils.py` | Removed `expected_output(s)`; added evaluables tests |
| `tests/pixie/evals/test_scorers.py` | Uses `Evaluable` model; updated priority tests |
| `tests/pixie/evals/test_trace_helpers.py` | Uses `Evaluable` instead of adapter classes |
| `tests/pixie/test_config.py` | Added `dataset_dir` tests |
| `tests/pixie/dataset/__init__.py` | New |
| `tests/pixie/dataset/test_models.py` | New — Dataset model tests |
| `tests/pixie/dataset/test_store.py` | New — DatasetStore CRUD tests |

## Migration Notes

This is a **breaking change**:

1. **Custom evaluators**: Any evaluator accepting `expected_output` as a kwarg must be updated to read `evaluable.expected_output` instead.
2. **`evaluate()` / `run_and_evaluate()`**: Remove `expected_output` kwarg. Set `expected_output` on the `Evaluable` instance instead.
3. **`assert_pass()`**: Remove `expected_outputs` kwarg. Use `evaluables` parameter with `Evaluable` items that have `expected_output` set.
4. **`ObserveSpanEval` / `LLMSpanEval`**: These classes no longer exist. Use `as_evaluable()` or construct `Evaluable` directly.
5. **`Evaluable` type checking**: `Evaluable` is no longer a Protocol — it's a Pydantic `BaseModel`. `isinstance()` checks will still work, but duck typing won't.
