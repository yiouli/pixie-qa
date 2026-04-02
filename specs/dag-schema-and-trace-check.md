# DAG Schema And Trace Check Semantics

## Purpose

Define the runtime contract for `pixie dag validate` and `pixie dag check-trace`.

## DAG node schema

Each DAG node is a JSON object with:

- `name` (required, string): unique lower_snake_case node identifier (for example, `handle_turn`)
- `code_pointer` (required, string): `path/to/file.py:function_name`
- `description` (required, string)
- `parent` (optional, string or null): parent node `name`
- `is_llm_call` (optional, boolean): defaults to `false`
- `metadata` (optional, object)

Backward compatibility:

- `parent_id` is accepted as a legacy alias for `parent` during parsing.

## Validation rules (`pixie dag validate`)

1. Top-level JSON value must be an array of objects.
2. Required fields must be present on every node.
3. Node names must be lower_snake_case.
4. Node names must be unique.
5. Every non-null `parent` must reference an existing node name.
6. Exactly one root node exists (`parent` is null/omitted).
7. Parent links must be acyclic.
8. `code_pointer` file path must exist relative to `--project-root` (or DAG file directory when omitted).

## Trace matching rules (`pixie dag check-trace`)

Given the latest captured trace:

1. If `is_llm_call=true`, the node is considered matched when at least one LLM span exists in the trace.
2. If `is_llm_call` is false/omitted, the node name must exactly match a non-LLM span name.
3. If a node is non-LLM but only an LLM span matches that name, report a flag mismatch error.
4. Extra spans are informational and do not fail the check.

## Mermaid generation

- Root nodes render as rounded nodes.
- `is_llm_call=true` nodes render as double-box nodes and include an `LLM` badge in the label.
- Other nodes render as standard rectangles.
