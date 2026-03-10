# Observation Store Module Implementation

## What Changed

Implemented the `pixie.storage` module for persisting and querying LLM application execution traces, as specified in `specs/storage.md`.

### New capabilities:

- **Evaluable protocol** (`evaluable.py`) — A `runtime_checkable` `Evaluable` protocol with `ObserveSpanEval` and `LLMSpanEval` adapters for uniform evaluator access to either span type. Includes `as_evaluable()` convenience function.
- **ObservationNode tree** (`tree.py`) — `ObservationNode` dataclass wrapping spans with delegated properties, `find(name)` / `find_by_type(cls)` search, and `to_text()` LLM-friendly serialization. `build_tree()` function assembles flat span lists into parent-child trees.
- **Serialization** (`serialization.py`) — `serialize_span()` and `deserialize_span()` for lossless round-trip conversion between frozen dataclass spans and JSON-safe dicts. Handles nested dataclasses, tuples ↔ lists, datetimes ↔ ISO strings.
- **Piccolo table** (`tables.py`) — `Observation` table with promoted columns for `trace_id`, `span_kind`, `name`, `error`, timestamps, and `duration_ms`, plus a `data` JSONB column for the full span payload.
- **ObservationStore** (`store.py`) — Async store with write (`save`, `save_many`), trace-level reads (`get_trace`, `get_trace_flat`), eval shortcuts (`get_root`, `get_last_llm`), component queries (`get_by_name`, `get_by_type`), investigation (`get_errors`), and browsing (`list_traces`).

### Dependencies added:

- `piccolo[sqlite]` — ORM and SQLite engine
- `pytest-asyncio` (dev) — async test support

## Files Affected

### New source files:

- `pixie/observation_store/__init__.py` — package exports
- `pixie/observation_store/evaluable.py` — Evaluable protocol and adapters
- `pixie/observation_store/tree.py` — ObservationNode and build_tree
- `pixie/observation_store/serialization.py` — span serialization/deserialization
- `pixie/observation_store/tables.py` — Piccolo Observation table
- `pixie/observation_store/store.py` — ObservationStore
- `pixie/observation_store/piccolo_conf.py` — SQLite engine config
- `pixie/observation_store/piccolo_migrations/__init__.py` — migration placeholder

### New test files:

- `tests/pixie/observation_store/__init__.py`
- `tests/pixie/observation_store/conftest.py` — shared span fixtures
- `tests/pixie/observation_store/test_evaluable.py` — 11 tests
- `tests/pixie/observation_store/test_tree.py` — 26 tests
- `tests/pixie/observation_store/test_serialization.py` — 11 tests
- `tests/pixie/observation_store/test_store.py` — 18 tests (async, temp SQLite)

### Modified files:

- `pyproject.toml` — added `piccolo[sqlite]` and `pytest-asyncio` dependencies
- `README.md` — added observation store section, usage example, and API reference
- `specs/storage.md` — unchanged (implementation follows spec as-is)

## Migration Notes

- No changes to existing `pixie.instrumentation` module or its tests.
- `ObserveSpan` and `LLMSpan` are imported, not modified — they remain frozen dataclasses.
- SQLite database defaults to `pixie_observations.db` in CWD; override via `PIXIE_DB_PATH` env var.
- Call `await store.create_tables()` before first use to initialize the schema.
