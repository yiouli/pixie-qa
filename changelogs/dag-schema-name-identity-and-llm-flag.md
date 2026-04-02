# DAG Schema: Name Identity And LLM Flag

## What changed

- Simplified DAG node schema by removing `id` and `type`.
- Made `name` the unique node identifier.
- Standardized DAG node names to lower_snake_case.
- Added optional `is_llm_call` boolean (defaults to `false`).
- Switched parent linkage to name-based references via `parent` (with legacy `parent_id` parsing support).
- Updated trace-check behavior:
  - `is_llm_call=true` nodes are validated by LLM-span presence.
  - Name matching is skipped for LLM nodes.
  - Non-LLM nodes require exact non-LLM span-name matches.
  - Added explicit mismatch errors when non-LLM nodes match only LLM spans.
- Updated Mermaid generation for the new schema and flags.

## Files affected

- `pixie/dag/__init__.py`
- `pixie/dag/trace_check.py`
- `tests/pixie/dag/test_dag.py`
- `tests/pixie/dag/test_trace_check.py`
- `docs/package.md`
- `specs/dag-schema-and-trace-check.md`

## Migration notes

- New DAG files should use:
  - required: `name`, `code_pointer`, `description`
  - optional: `parent`, `is_llm_call`, `metadata`
- DAG node `name` and `parent` values must use lower_snake_case (for example, `handle_turn`).
- Existing DAG files using `parent_id` continue to parse.
- Existing DAG files that rely on `id`/`type` should be migrated to the new schema.
