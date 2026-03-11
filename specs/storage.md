# Observation Storage Module — Implementation Spec

> **Note:** The `Evaluable` protocol described in section 1 has been superseded by
> `specs/dataset-management.md`. `Evaluable` is now a Pydantic `BaseModel` with an
> `expected_output` field and `_Unset` sentinel. The adapter classes `ObserveSpanEval`
> and `LLMSpanEval` have been removed; `as_evaluable()` now returns `Evaluable`
> model instances directly.

## Overview

A storage module for persisting and querying LLM application execution traces. A trace represents a single app execution (production or eval). Each trace contains observations (function/component invocations) forming a parent-child tree. Storage is backed by Piccolo ORM with SQLite as the default engine.

This module has three concerns:

1. **Evaluable protocol** — uniform interface for evaluators to extract data from either span type
2. **ObservationNode** — tree wrapper with traversal and LLM-friendly serialization
3. **Piccolo table + ObservationStore** — persistence and query API

The span data types (`ObserveSpan`, `LLMSpan`, and all message/tool types) already exist in the instrumentation module. This module imports and uses them directly — it does NOT redefine or duplicate them.

---

## 1. Evaluable Protocol

### File: `evaluable.py`

```python
@runtime_checkable
class Evaluable(Protocol):
    @property
    def eval_input(self) -> Any: ...

    @property
    def eval_output(self) -> Any: ...

    @property
    def eval_metadata(self) -> dict: ...
```

Neither `ObserveSpan` nor `LLMSpan` should be modified — they are frozen dataclasses in the instrumentation module. Instead, provide **adapter classes** that wrap them.

#### `class ObserveSpanEval`

A thin wrapper that takes an `ObserveSpan` and implements `Evaluable`.

- `eval_input` → returns `span.input`
- `eval_output` → returns `span.output`
- `eval_metadata` → returns `span.metadata`

#### `class LLMSpanEval`

A thin wrapper that takes an `LLMSpan` and implements `Evaluable`.

- `eval_input` → returns `span.input_messages` (the full `tuple[Message, ...]`)
- `eval_output` → extracts the content from the last output message:
  - If `span.output_messages` is non-empty, take `span.output_messages[-1]`
  - From that `AssistantMessage`, extract the text content: join all `TextContent` parts from `.content` tuple
  - If `output_messages` is empty, return `None`
- `eval_metadata` → returns a dict containing:
  - `"provider"`: `span.provider`
  - `"request_model"`: `span.request_model`
  - `"response_model"`: `span.response_model`
  - `"operation"`: `span.operation`
  - `"input_tokens"`: `span.input_tokens`
  - `"output_tokens"`: `span.output_tokens`
  - `"cache_read_tokens"`: `span.cache_read_tokens`
  - `"cache_creation_tokens"`: `span.cache_creation_tokens`
  - `"finish_reasons"`: `span.finish_reasons`
  - `"error_type"`: `span.error_type`
  - `"tool_definitions"`: `span.tool_definitions`

#### Helper function: `as_evaluable(span: ObserveSpan | LLMSpan) -> Evaluable`

Convenience function that returns `ObserveSpanEval(span)` or `LLMSpanEval(span)` based on type.

---

## 2. ObservationNode

### File: `tree.py`

Imports `ObserveSpan`, `LLMSpan`, and all message types from the instrumentation module.

```python
@dataclass
class ObservationNode:
    span: ObserveSpan | LLMSpan
    children: list[ObservationNode] = field(default_factory=list)
```

#### Delegated Properties

- `span_id` → `self.span.span_id`
- `trace_id` → `self.span.trace_id`
- `parent_span_id` → `self.span.parent_span_id`
- `name` → for `ObserveSpan`: `self.span.name or "(unnamed)"`; for `LLMSpan`: `self.span.request_model`
- `duration_ms` → `self.span.duration_ms`

#### `find(name: str) -> list[ObservationNode]`

Returns all nodes in the subtree (including self) where `node.name == name`. Depth-first traversal.

#### `find_by_type(span_type: type) -> list[ObservationNode]`

Returns all nodes in the subtree (including self) where `isinstance(node.span, span_type)` is True. This replaces string-based type matching — callers pass the actual class:

```python
llm_nodes = root.find_by_type(LLMSpan)
observe_nodes = root.find_by_type(ObserveSpan)
```

#### `to_text(indent: int = 0) -> str`

Serializes the tree to LLM-friendly indented outline.

**For `ObserveSpan`:**

```
{name} [{duration_ms:.0f}ms]
  input: {formatted_input}
  output: {formatted_output}
  <e>{error}</e>
  {children}
```

- `name` uses `span.name or "(unnamed)"`.
- If `span.input` is None → omit the `input:` line entirely.
- If `span.output` is None → omit the `output:` line entirely.
- If `span.error` is None → omit the `<e>` line entirely.
- If `span.metadata` is non-empty → add `metadata: {json}` line.

**For `LLMSpan`:**

```
{request_model} [{provider}, {duration_ms:.0f}ms]
  input_messages:
    {formatted messages, one per line}
  output:
    {formatted assistant message}
  tokens: {input_tokens} in / {output_tokens} out
  <e>{error_type}</e>
  {children}
```

- Header uses `request_model` as the name and `provider` in brackets.
- `input_messages`: each message on its own indented line. Format per message type:
  - `SystemMessage` → `system: {content}`
  - `UserMessage` → `user: {text of all TextContent parts joined}` (omit image detail for brevity)
  - `AssistantMessage` → `assistant: {text of all TextContent parts joined}` + if tool_calls non-empty: ` [tool_calls: {name1}, {name2}]`
  - `ToolResultMessage` → `tool({tool_name}): {content}`
- `output`: format `span.output_messages` the same way as AssistantMessage above. If empty, omit line.
- `tokens` line: always show if either `input_tokens` or `output_tokens` > 0. Include cache tokens if > 0: `tokens: 150 in / 42 out (30 cache read)`.
- If `span.error_type` is None → omit the `<e>` line.
- If `span.tool_definitions` is non-empty → add `tools: [{name1}, {name2}, ...]` line.

**Example output:**

```
rag_pipeline [402ms]
  input: {"query": "What is our refund policy?"}
  output: "You can return items within 30 days for a full refund."
  retrieve [52ms]
    input: {"query": "What is our refund policy?"}
    output: {"chunks": ["Returns accepted within 30 days..."]}
  gpt-4o [openai, 340ms]
    input_messages:
      system: You are a helpful assistant. Use the provided context to answer.
      user: What is our refund policy?
    output:
      assistant: You can return items within 30 days for a full refund.
    tokens: 150 in / 42 out
```

**Error example:**

```
rag_pipeline [5023ms]
  input: {"query": "What is our refund policy?"}
  <e>TimeoutError</e>
  retrieve [5001ms]
    input: {"query": "What is our refund policy?"}
    <e>ConnectionError</e>
```

**Formatting rules:**

- Indentation: 2 spaces per level.
- String values: rendered as-is.
- Dict/list values: `json.dumps(value, default=str)`.
- None values: entire field line omitted.
- `<e>` tag always on its own indented line.
- Children rendered after all field lines, each at `indent + 1`.

#### `build_tree(spans: list[ObserveSpan | LLMSpan]) -> list[ObservationNode]`

Module-level function. Takes a flat list of spans (all sharing the same `trace_id`), builds the tree, returns root node(s).

Algorithm:

1. Create an `ObservationNode` for each span.
2. Index by `span.span_id`.
3. For each node, if `span.parent_span_id` is not None and exists in the index, append to parent's `children`.
4. Otherwise, treat as root.
5. Sort each node's `children` by `span.started_at` ascending.
6. Return list of root nodes.

---

## 3. Piccolo Table

### File: `tables.py`

Single table named `observation`.

```python
class Observation(Table, tablename="observation"):
    id = Varchar(length=16, primary_key=True)     # span_id (hex, 16 chars)
    trace_id = Varchar(length=64, index=True)
    parent_span_id = Varchar(length=16, null=True, default=None)
    span_kind = Varchar(length=16)                 # "observe" or "llm"
    name = Varchar(length=256, null=True, index=True)
    data = JSONB()                                 # full span payload
    error = Text(null=True, default=None)
    started_at = Timestamptz()
    ended_at = Timestamptz()
    duration_ms = Real()
```

**Column notes:**

- `id` is `span_id` from the span — a 16-char hex string, not a UUID.
- `trace_id` is 32-char hex. Indexed — every read starts here.
- `parent_span_id` is NOT a foreign key constraint. Just a stored value for tree assembly in Python. This avoids insert-ordering issues since child spans end (and get saved) before parent spans.
- `span_kind` — `"observe"` for `ObserveSpan`, `"llm"` for `LLMSpan`. Used to pick the right deserializer.
- `name` — for `ObserveSpan`: `span.name` (can be null). For `LLMSpan`: `span.request_model`. Indexed for component-level queries.
- `data` — single JSONB column containing all span fields serialized as a dict. Serialization must handle: frozen dataclass instances → dicts recursively, `tuple` → `list`, `datetime` → ISO 8601 string.
- `error` — promoted to top-level column for `WHERE error IS NOT NULL`. Sourced from `ObserveSpan.error` or `LLMSpan.error_type`.
- `started_at`, `ended_at`, `duration_ms` — promoted for ordering and latency queries.

### File: `serialization.py`

#### `serialize_span(span: ObserveSpan | LLMSpan) -> dict`

Converts a span to a dict matching the table columns. Must:

1. Convert the frozen dataclass to a dict recursively (handle nested dataclasses, tuples → lists, datetimes → ISO strings).
2. Return a dict with keys: `id`, `trace_id`, `parent_span_id`, `span_kind`, `name`, `data`, `error`, `started_at`, `ended_at`, `duration_ms`.

#### `deserialize_span(row: dict) -> ObserveSpan | LLMSpan`

Reconstructs a span from a table row. Must:

1. Read `span_kind` to determine target type.
2. Reconstruct from `data` JSON, including nested types:
   - `Message` union → dispatch on `role`: `"system"` → `SystemMessage`, `"user"` → `UserMessage`, `"assistant"` → `AssistantMessage`, `"tool"` → `ToolResultMessage`
   - `MessageContent` union → dispatch on `type`: `"text"` → `TextContent`, `"image"` → `ImageContent`
   - `ToolCall`, `ToolDefinition` → reconstruct from dicts
   - `list` → `tuple` for all tuple-typed fields
   - ISO strings → `datetime` for timestamp fields
3. All fields on the reconstructed span must match the original. This is the highest-risk code in the module.

### File: `piccolo_conf.py`

```python
DB = SQLiteEngine(path=os.environ.get("PIXIE_DB_PATH", "pixie_observations.db"))
```

### File: `piccolo_migrations/0001_initial.py`

Create the `observation` table.

---

## 4. ObservationStore

### File: `store.py`

#### Constructor

```python
class ObservationStore:
    def __init__(self, engine: SQLiteEngine | None = None):
        """If engine is None, use the default from piccolo_conf."""
```

#### Write Methods

##### `async save(span: ObserveSpan | LLMSpan) -> None`

Serialize the span to a row and insert. Single insert.

##### `async save_many(spans: list[ObserveSpan | LLMSpan]) -> None`

Batch insert via Piccolo's bulk insert. Order does not matter.

#### Read Methods — Trace Level

##### `async get_trace(trace_id: str) -> list[ObservationNode]`

1. Query all rows `WHERE trace_id = ?`.
2. Deserialize each row to `ObserveSpan` or `LLMSpan`.
3. Call `build_tree()`.
4. Return root node(s). Empty list if not found.

##### `async get_trace_flat(trace_id: str) -> list[ObserveSpan | LLMSpan]`

All spans for a trace as flat list, ordered by `started_at` ascending. No tree assembly.

#### Read Methods — Eval Shortcuts

##### `async get_root(trace_id: str) -> ObserveSpan`

Query `WHERE trace_id = ? AND parent_span_id IS NULL`. Return as `ObserveSpan`.

Raise `ValueError` if not found. If multiple roots, return earliest `started_at`.

Returns raw span, not `ObservationNode` — callers doing run-level eval need the `Evaluable` interface, not tree structure.

##### `async get_last_llm(trace_id: str) -> LLMSpan | None`

Query `WHERE trace_id = ? AND span_kind = 'llm' ORDER BY ended_at DESC LIMIT 1`.

Return as `LLMSpan`, or `None` if no LLM spans in the trace.

#### Read Methods — Component Level

##### `async get_by_name(name: str, trace_id: str | None = None) -> list[ObserveSpan | LLMSpan]`

Query `WHERE name = ?`, optionally `AND trace_id = ?`. Flat list, ordered by `started_at`.

##### `async get_by_type(span_kind: str, trace_id: str | None = None) -> list[ObserveSpan | LLMSpan]`

Query `WHERE span_kind = ?` (`"observe"` or `"llm"`), optionally scoped to trace. Ordered by `started_at`.

#### Read Methods — Investigation

##### `async get_errors(trace_id: str | None = None) -> list[ObserveSpan | LLMSpan]`

Query `WHERE error IS NOT NULL`, optionally scoped to trace. Ordered by `started_at`.

##### `async list_traces(limit: int = 50, offset: int = 0) -> list[dict]`

Lightweight trace listing for browsing. Each dict:

```python
{
    "trace_id": str,
    "root_name": str | None,   # name column of the root observation
    "started_at": datetime,     # started_at of the root observation
    "has_error": bool,          # True if ANY observation in trace has error IS NOT NULL
    "observation_count": int,
}
```

Ordered by `started_at` descending (most recent first). Implement efficiently with aggregation, not N+1. Apply `limit` and `offset`.

---

## 5. Tests

### `tests/test_evaluable.py`

- `ObserveSpanEval` wrapping an `ObserveSpan` satisfies `isinstance(..., Evaluable)`.
- `LLMSpanEval` wrapping an `LLMSpan` satisfies `isinstance(..., Evaluable)`.
- `LLMSpanEval.eval_input` returns the full `input_messages` tuple.
- `LLMSpanEval.eval_output` returns joined text of last `AssistantMessage` when `output_messages` is non-empty.
- `LLMSpanEval.eval_output` returns `None` when `output_messages` is empty.
- `LLMSpanEval.eval_metadata` includes `provider`, `request_model`, `input_tokens`, `output_tokens`, etc.
- `ObserveSpanEval.eval_input` returns `span.input`.
- `ObserveSpanEval.eval_output` returns `span.output`.
- `as_evaluable()` returns correct wrapper type for each span type.

### `tests/test_tree.py`

- `build_tree` with single root returns one node with empty children.
- `build_tree` with parent-child spans produces correct nesting.
- `build_tree` sorts children by `started_at`.
- `build_tree` handles orphaned spans (parent_span_id points to nonexistent span) as additional roots.
- `find("name")` returns matching descendants.
- `find_by_type(LLMSpan)` returns all LLM nodes in subtree.
- `find` on non-existent name returns empty list.
- `to_text()` for `ObserveSpan` node outputs correct format with name, duration, input, output.
- `to_text()` for `LLMSpan` node includes model name, provider, input_messages, output, token counts.
- `to_text()` with error includes `<e>` tag.
- `to_text()` omits lines for None fields.
- `to_text()` for nested tree produces correct multi-level indentation.
- `to_text()` formats `UserMessage` with `TextContent` parts correctly.
- `to_text()` formats `AssistantMessage` with `ToolCall`s correctly.
- `to_text()` shows cache tokens when > 0.

### `tests/test_serialization.py`

Round-trip tests — highest-risk code in the module.

- `ObserveSpan` → serialize → deserialize → equals original.
- `LLMSpan` → serialize → deserialize → equals original.
- `LLMSpan` with `SystemMessage` + `UserMessage` + `AssistantMessage` round-trips correctly.
- `LLMSpan` with `ToolCall`s and `ToolResultMessage` round-trips correctly.
- `LLMSpan` with `ImageContent` in `UserMessage` round-trips correctly.
- `LLMSpan` with empty `output_messages` round-trips correctly.
- `ObserveSpan` with complex nested dict/list `input` round-trips correctly.
- `ObserveSpan` with `None` input/output round-trips correctly.
- Tuples preserved through serialize (→list) → deserialize (→tuple) cycle.
- Datetimes preserved through serialize (→ISO) → deserialize (→datetime) cycle.

### `tests/test_store.py`

Async tests with temp SQLite database.

- `save` + `get_trace` round-trips an `ObserveSpan`.
- `save` + `get_trace` round-trips an `LLMSpan`.
- `save_many` + `get_trace` builds correct tree.
- `save_many` works regardless of insert order (child before parent).
- `get_trace_flat` returns flat list ordered by `started_at`.
- `get_root` returns `ObserveSpan` with `parent_span_id IS NULL`.
- `get_root` raises `ValueError` for nonexistent trace.
- `get_last_llm` returns `LLMSpan` with latest `ended_at`.
- `get_last_llm` returns `None` when no LLM spans exist.
- `get_by_name` filters by name within a trace.
- `get_by_name` without trace_id returns across all traces.
- `get_by_type("llm")` returns only `LLMSpan` instances.
- `get_errors` returns only spans with non-null error.
- `get_errors` scoped to trace filters correctly.
- `list_traces` returns correct summary dicts.
- `list_traces` orders most recent first.
- `list_traces` respects limit and offset.
- `list_traces` reports `has_error=True` when any observation has error.

---

## 6. File Structure

```
pixie/
├── observation_store/
│   ├── __init__.py          # exports Evaluable, ObserveSpanEval, LLMSpanEval,
│   │                        #   as_evaluable, ObservationNode, build_tree,
│   │                        #   ObservationStore
│   ├── evaluable.py         # Evaluable protocol, ObserveSpanEval, LLMSpanEval, as_evaluable
│   ├── tree.py              # ObservationNode, build_tree
│   ├── tables.py            # Piccolo Observation table
│   ├── serialization.py     # serialize_span, deserialize_span
│   ├── store.py             # ObservationStore
│   ├── piccolo_conf.py
│   └── piccolo_migrations/
│       └── 0001_initial.py
└── tests/
    └── observation_store/
        ├── test_evaluable.py
        ├── test_tree.py
        ├── test_serialization.py
        └── test_store.py
```

---

## 7. Dependencies

- `piccolo[sqlite]` — already in the project
- Imports from instrumentation module: `ObserveSpan`, `LLMSpan`, `SystemMessage`, `UserMessage`, `AssistantMessage`, `ToolResultMessage`, `TextContent`, `ImageContent`, `ToolCall`, `ToolDefinition`
- Python ≥ 3.11
- No new external dependencies

---

## 8. Non-Goals

- **Scores / evaluation results** — not stored here. Evaluators consume spans via `Evaluable` but store results elsewhere.
- **Datasets** — separate concern.
- **The `@observe` decorator** — this is the storage backend the decorator writes to. Decorator is separate.
- **Modifying existing span types** — `ObserveSpan` and `LLMSpan` are frozen dataclasses owned by the instrumentation module. This module wraps them, does not change them.
- **Postgres / Supabase migration** — SQLite only for now.
- **Web UI / API layer** — this is a library.
