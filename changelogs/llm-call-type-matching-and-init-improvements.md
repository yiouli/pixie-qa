# llm_call type-based matching & init improvements

## What changed

### 1. `dag check-trace`: llm_call nodes matched by type, not name

Previously, all observable DAG node types (`entry_point`, `observation`, `llm_call`) were
matched against trace spans by exact `name` comparison. This was fragile for `llm_call`
nodes because model identifiers can be resolved by the runtime (e.g., `"gpt-4o-mini"` →
`"gpt-4o-mini-2024-07-18"`), causing false mismatches.

Now, `llm_call` nodes are matched by **type**: the check passes if at least one LLM span
(type `"llm_call"`) exists anywhere in the trace. The DAG node `name` is no longer compared
for `llm_call` nodes. `entry_point` and `observation` nodes still use exact name matching.

### 2. `pixie init`: creates `scripts/__init__.py`

`pixie init` now creates an empty `__init__.py` inside the `scripts/` subdirectory after
creating the directory structure. This allows test files to import from `pixie_qa.scripts`
without the agent needing to manually create the init file.

## Files affected

- `pixie/dag/trace_check.py` — type-based matching for llm_call, track matched span names
- `pixie/cli/init_command.py` — create `scripts/__init__.py`
- `tests/pixie/dag/test_trace_check.py` — updated existing tests, added `test_llm_call_matches_by_type_not_name` and `test_llm_call_fails_when_no_llm_spans`
- `tests/pixie/cli/test_init_command.py` — added assertion for `scripts/__init__.py`

## Migration notes

- DAGs should use `"call_llm"` as the standard name for all `llm_call` nodes and place the
  actual model identifier in `metadata.model`. The name is no longer used for matching.
- No breaking API changes — existing DAGs with model names as `llm_call` node names will
  still pass `check-trace` (since matching is now type-based).
