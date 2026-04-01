# DAG Validation and Trace Check

## What changed

Added a new `pixie dag` CLI subcommand with two operations:

1. **`pixie dag validate <dag_json_path>`** — Validates a data-flow DAG JSON file and generates a Mermaid flowchart diagram on success.
2. **`pixie dag check-trace <dag_json_path>`** — Validates the most recent captured trace against a DAG, checking that every observable node has a corresponding span.

Also made `openinference-instrumentation-openai` a default dependency (was optional-only) and added logging to the instrumentors module.

## Files affected

### New files

- `pixie/dag/__init__.py` — DAG model (`DagNode`), parsing, validation, Mermaid generation
- `pixie/dag/trace_check.py` — Trace-vs-DAG validation
- `pixie/cli/dag_command.py` — CLI entry points for `pixie dag validate` and `pixie dag check-trace`
- `tests/pixie/dag/__init__.py` — Test package
- `tests/pixie/dag/test_dag.py` — 18 tests for DAG validation
- `tests/pixie/dag/test_trace_check.py` — 6 tests for trace checking

### Modified files

- `pixie/cli/main.py` — Added `dag` subparser with `validate` and `check-trace` subcommands
- `pixie/instrumentation/instrumentors.py` — Added logging for instrumentor activation
- `pyproject.toml` — Added `openinference-instrumentation-openai>=0.1.4` to default deps

## DAG JSON schema

Each node in the DAG JSON array has:

- `id` (string) — unique identifier
- `name` (string) — human-readable name
- `type` (string) — one of: `entry_point`, `llm_call`, `data_dependency`, `intermediate_state`, `side_effect`, `observation`
- `code_pointer` (string) — file path and function name
- `description` (string) — what the node does
- `parent_id` (string | null) — parent node ID (null for root)
- `metadata` (object, optional) — additional info

## Migration notes

No breaking changes. The new CLI commands are purely additive.
