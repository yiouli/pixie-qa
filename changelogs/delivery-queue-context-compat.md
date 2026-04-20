# Delivery Queue Context Compatibility

## What changed and why

`_DeliveryQueue` preserved `ContextVar` state by creating handler tasks with
`asyncio.create_task(..., context=ctx)`. That works on Python 3.11+, but the
project currently supports Python 3.10 as well. On 3.10 the `context=` keyword
is not accepted, so async handler delivery failed before the coroutine was
scheduled. The queue swallowed the exception, which left LLM spans undelivered
and caused processor, queue, and trace-capture tests to fail.

The queue now creates the child task while the copied context is active via
`ctx.run(...)`. That preserves `current_entry_index` propagation for per-entry
trace capture without relying on a Python-version-specific task API.

## Files affected

- `pixie/instrumentation/llm_tracing.py`
- `specs/instrumentation.md`
- `tests/pixie/instrumentation/test_queue.py`
- `tests/pixie/instrumentation/test_processor.py`
- `tests/pixie/harness/test_trace_capture.py`

## Migration notes

No public API changed. This is a runtime-compatibility fix for async handler
delivery on Python 3.10.
