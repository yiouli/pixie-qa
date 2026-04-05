# Instrumentation API Reference

> Auto-generated from pixie source code docstrings.
> Do not edit by hand — run `uv run python scripts/generate_skill_docs.py`.

pixie.instrumentation — public API for tracing and observing LLM applications.

Core functions:
    - ``init()`` — initialize the tracer provider.
    - ``observe`` — decorator for automatic function input/output capture.
    - ``start_observation()`` — context-manager for manual observation blocks.
    - ``flush()`` — flush pending spans to handlers.
    - ``add_handler()`` / ``remove_handler()`` — register span handlers.
    - ``enable_storage()`` — enable SQLite-backed span persistence.

Configuration
-------------

| Variable | Default | Description |
| --- | --- | --- |
| ``PIXIE_ROOT`` | ``pixie_qa`` | Root directory for all pixie-generated artefacts |
| ``PIXIE_DB_PATH`` | ``{PIXIE_ROOT}/pixie.db`` | SQLite database for captured spans |
| ``PIXIE_DATASET_DIR`` | ``{PIXIE_ROOT}/datasets`` | Directory for dataset JSON files |

CLI Commands
------------

| Command | Description |
| --- | --- |
| ``pixie init [root]`` | Scaffold the ``pixie_qa`` working directory |
| ``pixie trace list [--limit N] [--errors]`` | List recent traces |
| ``pixie trace show <trace_id> [-v] [--json]`` | Show span tree for a trace |
| ``pixie trace last [--json]`` | Show the most recent trace (verbose) |
| ``pixie trace verify`` | Verify the most recent trace for common issues |
| ``pixie dag validate <json>`` | Validate a DAG JSON file |
| ``pixie dag check-trace <json>`` | Check the last trace against a DAG |

---

## Functions

### `pixie.init`

```python
pixie.init(*, capture_content: 'bool' = True, queue_size: 'int' = 1000) -> 'None'
```

Initialize the instrumentation sub-package.

Sets up the OpenTelemetry ``TracerProvider``, span processor, delivery
queue, and activates auto-instrumentors.  Truly idempotent — calling
``init()`` a second time is a no-op.

Handler registration is done separately via :func:`add_handler`.

### `pixie.observe`

```python
pixie.observe(name: 'str | None' = None) -> 'Callable[[Callable[P, T]], Callable[P, T]]'
```

Decorator that wraps a function in a start_observation() block.

Automatically captures the function's keyword arguments as input and
the return value as output. Uses jsonpickle for serialization.

If tracing is not initialized, the function executes normally with no
overhead beyond the decorator call itself.

Args:
    name: Optional span name. Defaults to the function's __name__.

### `pixie.start_observation`

```python
pixie.start_observation(*, input: 'JsonValue', name: 'str | None' = None) -> 'Generator[ObservationContext, None, None]'
```

Context manager that creates an OTel span and yields a mutable ObservationContext.

If init() has not been called, yields a no-op context — the wrapped code
executes normally but no span is captured.

### `pixie.flush`

```python
pixie.flush(timeout_seconds: 'float' = 5.0) -> 'bool'
```

Flush the delivery queue, blocking until all items are processed.

### `pixie.add_handler`

```python
pixie.add_handler(handler: 'InstrumentationHandler') -> 'None'
```

Register *handler* to receive span notifications.

Must be called after :func:`init`.  Multiple handlers can be
registered; each receives every span.

### `pixie.remove_handler`

```python
pixie.remove_handler(handler: 'InstrumentationHandler') -> 'None'
```

Unregister a previously registered *handler*.

Raises ``ValueError`` if *handler* was not registered.

### `pixie.enable_storage`

```python
pixie.enable_storage() -> 'StorageHandler'
```

Set up Piccolo storage with default config and register the handler.

Creates the ``pixie_qa`` root directory and observation table if they
don't exist.  Truly idempotent — calling twice returns the same
handler without duplicating registrations, even from different threads
or from within an async context.

Returns:
    The :class:`StorageHandler` for optional manual control.
