# Root Package Re-exports and Evaluable trace_id

## What Changed

### 1. Full public API re-exported from `pixie` root package

Previously, `pixie/__init__.py` only exported `enable_storage` and `StorageHandler`. Users (and the eval-driven-dev skill) had to use submodule imports like `import pixie.instrumentation as px`, `from pixie.evals import ...`, `from pixie.dataset.store import DatasetStore`, and `from pixie.storage.evaluable import Evaluable`.

Now **every public symbol** is importable from the top-level `pixie` package:

```python
from pixie import observe, flush, start_observation, init, add_handler
from pixie import assert_dataset_pass, FactualityEval, ScoreThreshold, last_llm_call, root
from pixie import DatasetStore, Evaluable, ObservationStore, UNSET
```

This eliminates Pylance resolution errors for downstream users and simplifies the import story.

### 2. `as_evaluable()` now includes `trace_id` and `span_id` in metadata

Both `_observe_span_to_evaluable()` and `_llm_span_to_evaluable()` now inject the span's `trace_id` and `span_id` into `eval_metadata`. This means:

- `pixie dataset save` automatically includes trace provenance in the dataset
- Users can always look up the original trace for any dataset item
- The skill's investigation flow ("look up trace_id from metadata") actually works

### 3. Skill instructions updated

- **Stage 0**: Now verifies `OPENAI_API_KEY` (or equivalent) before running anything
- **Stage 3**: All code examples use `from pixie import ...` (no submodule imports)
- **Stage 4**: Test file example uses `from pixie import ...`
- **Stage 5**: Dataset building now emphasizes actually running the app to capture real outputs and traces; removed the misleading "Option B" that built datasets with fabricated/null outputs
- **Stage 7**: Investigation examples use `from pixie import DatasetStore, ObservationStore`
- **API reference**: All imports updated to top-level

## Files Affected

### Package
- `pixie/__init__.py` — re-exports all public API symbols
- `pixie/storage/evaluable.py` — `as_evaluable()` includes trace_id/span_id

### Tests
- `tests/pixie/test_init.py` — **new** — 27 tests verifying root package exports
- `tests/pixie/observation_store/test_evaluable.py` — added trace_id/span_id assertions

### Docs
- `README.md` — code examples updated to top-level imports
- `docs/package.md` — all import examples updated
- `.claude/skills/eval-driven-dev/SKILL.md` — full skill instruction rewrite
- `.claude/skills/eval-driven-dev/references/pixie-api.md` — API reference import paths

## Migration Notes

- **No breaking changes.** Submodule imports (`from pixie.evals import ...`, `import pixie.instrumentation as px`) continue to work. The top-level re-exports are purely additive.
- `eval_metadata` from `as_evaluable()` now always contains `trace_id` and `span_id` keys. Code that checks `eval_metadata is None` for ObserveSpans with no user metadata should instead check for specific keys.
