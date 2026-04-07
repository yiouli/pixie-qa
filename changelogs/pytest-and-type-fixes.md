# pytest and type fixes

## What changed

- Restored immutability for `WrappedData` by enabling frozen Pydantic model config.
- Updated dataset execution fallback in `pixie test` so `eval_output` is populated from runnable return values when no wrap output is captured.
- Switched web UI opener usage in CLI to module-level dispatch so patching in tests works reliably.
- Tightened typing in test helpers (`JsonValue`-based inputs/outputs) and adjusted scorer test doubles for strict mypy/Pylance compatibility.
- Replaced direct optional attribute access in docs generation script with `getattr` guard for Pylance compatibility.

## Files affected

- `pixie/instrumentation/wrap.py`
- `pixie/cli/test_command.py`
- `tests/pixie/instrumentation/test_wrap_log.py`
- `tests/pixie/instrumentation/test_spans.py`
- `tests/pixie/eval/test_llm_evaluator.py`
- `tests/pixie/eval/test_scorers.py`
- `tests/pixie/eval/test_runnable.py`
- `scripts/generate_skill_docs.py`

## Migration notes

- `WrappedData` instances are immutable after creation. Mutation now raises validation errors.
- No public API signature changes.
