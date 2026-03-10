# Async Handler Processing

## What changed and why

The instrumentation delivery pipeline was synchronous — handler methods were plain `def`,
the delivery queue ran handlers on a single background thread, and multiple handlers for the
same span were called sequentially. This made it hard to write handlers that do I/O (HTTP
calls, async DB writes, etc.) without blocking the pipeline.

Three improvements were made together:

### 1. Async handler interface

`InstrumentationHandler.on_llm` and `on_observe` are now `async def` coroutines. Handlers
can freely `await` inside their methods (e.g. `await db.save(span)`). The base-class
default implementations are still no-ops; existing subclasses only need to add `async`.

### 2. Concurrent multi-handler dispatch

`_HandlerRegistry` now dispatches all registered handlers concurrently via
`asyncio.gather(..., return_exceptions=True)` instead of a sequential `for` loop. When
multiple handlers are registered every one of them runs at the same time for each span.
Exceptions from any handler are collected by `return_exceptions=True` and discarded, so
one crashing handler can never block the others.

### 3. Fire-and-forget queue worker

`_DeliveryQueue` now owns a dedicated asyncio event loop running on a daemon thread
(`pixie-asyncio-loop`). The queue-consumer thread (`pixie-delivery-worker`) schedules
each span's dispatch coroutine with `asyncio.run_coroutine_threadsafe()` and then
**immediately loops** back to pick up the next item — it does not await the coroutine's
completion. `queue.task_done()` is called through a `Future` done-callback once the
coroutine finishes, so `flush()` / `queue.join()` still correctly blocks until all
in-flight async processing is complete.

### 4. `capture_content=True` by default

`init()` now defaults to `capture_content=True` (was `False`). Message content is
almost always needed for debugging and evaluation, so the opt-out default better reflects
real usage.

---

## Files affected

| File                                          | Change                                                                                                                               |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `pixie/instrumentation/handler.py`            | `on_llm` / `on_observe` → `async def`; `_HandlerRegistry` uses `asyncio.gather(return_exceptions=True)` for concurrent dispatch      |
| `pixie/instrumentation/queue.py`              | Added asyncio event loop thread; worker is now fire-and-forget via `run_coroutine_threadsafe` + done-callback                        |
| `pixie/instrumentation/__init__.py`           | `init()` default `capture_content=True`                                                                                              |
| `pixie/evals/trace_capture.py`                | `MemoryTraceHandler.on_llm` / `on_observe` → `async def`                                                                             |
| `tests/pixie/instrumentation/conftest.py`     | `RecordingHandler` methods → `async def`                                                                                             |
| `tests/pixie/instrumentation/test_queue.py`   | Updated `BlockingHandler` / `CrashingHandler` to async; added `TestDeliveryQueueFireAndForget`                                       |
| `tests/pixie/instrumentation/test_handler.py` | **New** — `TestHandlerRegistryConcurrency` and `TestHandlerRegistryErrorIsolation`                                                   |
| `tests/pixie/evals/test_trace_capture.py`     | Direct handler calls wrapped in `asyncio.run()`                                                                                      |
| `specs/instrumentation.md`                    | Updated handler interface, `_HandlerRegistry`, `_DeliveryQueue`, `init()` params, error handling rules, tests section, example usage |
| `README.md`                                   | Updated quick-start handler example to `async def`; updated `init()` API reference                                                   |

---

## Migration notes

**Handler implementations must become async:**

```python
# Before
class MyHandler(InstrumentationHandler):
    def on_llm(self, span: LLMSpan) -> None:
        db.save(span)

    def on_observe(self, span: ObserveSpan) -> None:
        db.save(span)

# After
class MyHandler(InstrumentationHandler):
    async def on_llm(self, span: LLMSpan) -> None:
        await db.save_async(span)  # or use asyncio.to_thread for sync I/O

    async def on_observe(self, span: ObserveSpan) -> None:
        await db.save_async(span)
```

If your handler does only synchronous work, simply add `async`:

```python
class MyHandler(InstrumentationHandler):
    async def on_llm(self, span: LLMSpan) -> None:
        print(span)  # sync body is fine inside async def
```

**`capture_content` default changed** — if you were relying on content being suppressed by
default, pass `capture_content=False` explicitly:

```python
px.init(capture_content=False)
```
