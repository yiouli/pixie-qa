# Wrap API Reference

> Auto-generated from pixie source code docstrings.
> Do not edit by hand — run `uv run python scripts/generate_skill_docs.py`.

``pixie.wrap`` — data-oriented observation API.

``wrap()`` observes a data value or callable at a named point in the
processing pipeline.  Its behavior depends on the active mode:

- **No-op** (tracing disabled, no eval registry): returns ``data`` unchanged.
- **Tracing** (``PIXIE_TRACING=1``): writes to the trace file and emits an
  OTel event (via span event if a span is active, or via OTel logger
  otherwise) and returns ``data`` unchanged (or wraps a callable so the
  event fires on call).
- **Eval** (eval registry active): injects dependency data for
  ``purpose="input"``, captures output/state for ``purpose="output"``/
  ``purpose="state"``.

---

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `PIXIE_TRACING` | unset | Set to `1` to enable tracing mode for `wrap()`.  When unset, `wrap()` is a no-op at runtime (eval mode is controlled by the test runner via the wrap registry, independent of this flag). |
| `PIXIE_TRACE_OUTPUT` | unset | Path to a JSONL file where `wrap()` events and LLM spans are written during a tracing run.  Requires `PIXIE_TRACING=1`. |

## CLI Commands

| Command | Description |
| --- | --- |
| `pixie trace filter <file.jsonl> --purpose entry,input` | Print only wrap events matching the given purposes.  Outputs one JSON line per matching event. |

---

## Functions

### `pixie.wrap`

```python
pixie.wrap(data: 'T', *, purpose: "Literal['entry', 'input', 'output', 'state']", name: 'str', description: 'str | None' = None) -> 'T'
```

Observe a data value or data-provider callable at a point in the processing pipeline.

``data`` can be either a plain value or a callable that produces a value.
In both cases the return type is ``T`` — the caller gets back exactly the
same type it passed in when in no-op or tracing modes.

In eval mode with ``purpose="input"``, the returned value (or callable) is
replaced with the deserialized registry value.  When ``data`` is callable
the returned wrapper ignores the original function and returns the injected
value on every call; in all other modes the returned callable wraps the
original and adds tracing or capture behaviour.

Args:
    data: A data value or a data-provider callable.
    purpose: Classification of the data point:
        - "entry": app input via entry point (user message, request body)
        - "input": data from external dependencies (DB records, API responses)
        - "output": data going out to external systems or users
        - "state": intermediate state for evaluation (routing decisions, etc.)
    name: Unique identifier for this data point. Used as the key in the
        eval registry and in trace logs.
    description: Optional human-readable description of what this data is.

Returns:
    The original data unchanged (tracing / no-op modes), or the
    registry value (eval mode with purpose="input").  When ``data``
    is callable the return value is also callable.

### `pixie.enable_storage`

```python
pixie.enable_storage() -> 'StorageHandler'
```

Set up Piccolo storage with default config and register the handler.

Creates the ``pixie_qa`` root directory and observation table if they
don't exist.  Truly idempotent — calling twice returns the same
handler without duplicating registrations, even from different threads
or from within an async context.

When ``PIXIE_TRACING=1`` and ``PIXIE_TRACE_OUTPUT`` is set, a
:class:`~pixie.instrumentation.trace_writer.TraceFileWriter` is also
created and stored at the module level for ``wrap()`` and
``LLMSpanProcessor`` to use.

Returns:
    The :class:`StorageHandler` for optional manual control.

---

## Error Types

### `WrapRegistryMissError`

```python
WrapRegistryMissError(name: 'str') -> 'None'
```

Raised when a wrap(purpose="input") name is not found in the eval registry.

### `WrapTypeMismatchError`

```python
WrapTypeMismatchError(name: 'str', expected_type: 'type', actual_type: 'type') -> 'None'
```

Raised when deserialized registry value doesn't match expected type.

---

## Trace File Utilities

Pydantic model for wrap log entries and JSONL loading utilities.

``WrapLogEntry`` is the typed representation of a single ``wrap()`` event
as recorded in a JSONL trace file.  Multiple places in the codebase load
these objects — the ``pixie trace filter`` CLI, the dataset loader, and
the verification scripts — so they share this single model.

### `pixie.WrapLogEntry`

```python
pixie.WrapLogEntry(*, type: str = 'wrap', name: str, purpose: str, data: Any, description: str | None = None, trace_id: str | None = None, span_id: str | None = None) -> None
```

A single wrap() event as logged to a JSONL trace file.

Attributes:
    type: Always ``"wrap"`` for wrap events.
    name: The wrap point name (matches ``wrap(name=...)``).
    purpose: One of ``"entry"``, ``"input"``, ``"output"``, ``"state"``.
    data: The serialized data (jsonpickle string).
    description: Optional human-readable description.
    trace_id: OTel trace ID (if available).
    span_id: OTel span ID (if available).

### `pixie.load_wrap_log_entries`

```python
pixie.load_wrap_log_entries(jsonl_path: 'str | Path') -> 'list[WrapLogEntry]'
```

Load all wrap log entries from a JSONL file.

Skips non-wrap lines (e.g. ``type=llm_span``) and malformed lines.

Args:
    jsonl_path: Path to a JSONL trace file.

Returns:
    List of :class:`WrapLogEntry` objects.

### `pixie.filter_by_purpose`

```python
pixie.filter_by_purpose(entries: 'list[WrapLogEntry]', purposes: 'set[str]') -> 'list[WrapLogEntry]'
```

Filter wrap log entries by purpose.

Args:
    entries: List of wrap log entries.
    purposes: Set of purpose values to include.

Returns:
    Filtered list.
