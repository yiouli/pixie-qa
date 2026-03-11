# Manual Instrumentation Usability — Implementation Spec

## Overview

A set of improvements to the manual instrumentation API in `pixie.instrumentation` that make it simpler, safer, and more ergonomic:

1. **`log()` → `start_observation()` rename** — already done. Update all remaining references, docstrings, comments, and tests to use the new name and signature (`input` is now a required keyword-only argument typed as `JsonValue`).
2. **`span` → `observation` variable naming convention** — rename the yielded context variable from `span` to `observation` in all call sites to better reflect what the context manager produces.
3. **No-op when tracing is not initialized** — `start_observation()` and `observe()` silently yield a no-op context instead of raising `RuntimeError` when `init()` has not been called, so instrumented code works with or without tracing.
4. **`@observe` decorator** — new decorator for wrapping functions with automatic input/output capture, using `jsonpickle` for serialization.

---

## 1. `log()` → `start_observation()` Signature Change

### Status: Signature already updated

The function has been renamed from `log()` to `start_observation()` and the `input` parameter is now a **required** keyword-only argument typed as `JsonValue` (from pydantic), aligning with the `input` field type used in `Evaluable`.

### Current signature

```python
@contextmanager
def start_observation(
    *,
    input: JsonValue,
    name: str | None = None,
) -> Generator[ObservationContext, None, None]:
```

### Remaining work

Update all stale references across the codebase:

| Location                                         | Change                                                                                |
| ------------------------------------------------ | ------------------------------------------------------------------------------------- |
| `pixie/instrumentation/__init__.py` line 1       | Module docstring still says `log()` — update to `start_observation()`                 |
| `pixie/instrumentation/context.py` line 1        | Docstring says "yielded by log()" — update to "yielded by start_observation()"        |
| `pixie/instrumentation/context.py` line 23       | Class docstring says "yielded by log()" — update                                      |
| `.github/copilot-instructions.md` line 22        | Comment says `# public API: init(), log(), flush()` — update to `start_observation()` |
| `.github/copilot-instructions.md` line 25        | Comment says "mutable object yielded by log()" — update                               |
| `.github/copilot-instructions.md` line 495       | "`log()` block exceptions" — update                                                   |
| `specs/instrumentation.md`                       | Multiple references to `log()` — update throughout                                    |
| All test docstrings/comments referencing `log()` | Update to `start_observation()`                                                       |

Update all call sites that pass `input` as optional or omit it:

```python
# ❌ Old — input was optional
with px.start_observation() as span:
    pass

# ✅ New — input is required
with px.start_observation(input=None) as observation:
    pass
```

Test files that need `input=` added where currently omitted:

- `tests/pixie/instrumentation/test_context.py` — lines 28, 62, 71, 100
- `tests/pixie/instrumentation/test_integration.py` — line 147, 149, and others where `input` is missing

---

## 2. `span` → `observation` Variable Naming Convention

### Motivation

When using `start_observation()`, the yielded `ObservationContext` object is typically named `span`:

```python
with px.start_observation(input=query) as span:
    span.set_output(answer)
```

This is confusing because `span` implies an OTel span primitive. The yielded object represents an **observation** — a higher-level concept. Rename to `observation` at all call sites.

### Change pattern

```python
# ❌ Old convention
with px.start_observation(input=query, name="qa") as span:
    span.set_output(answer)
    span.set_metadata("key", value)

# ✅ New convention
with px.start_observation(input=query, name="qa") as observation:
    observation.set_output(answer)
    observation.set_metadata("key", value)
```

### Files to update

All test files and example code that use `as span:` with `start_observation()`:

| File                                              | Lines                 |
| ------------------------------------------------- | --------------------- |
| `tests/pixie/instrumentation/test_context.py`     | lines 19, 28, 44      |
| `tests/pixie/instrumentation/test_integration.py` | lines 89, 113         |
| `tests/pixie/evals/test_eval_utils.py`            | lines 30, 36, 42, 43  |
| `tests/pixie/evals/test_trace_capture.py`         | lines 160, 170, 176   |
| `specs/instrumentation.md`                        | Example usage section |

**Note:** The `ObservationContext` class name itself is already correct — only the variable name at call sites needs updating.

---

## 3. No-Op When Tracing Is Not Initialized

### Motivation

Currently, `start_observation()` raises `RuntimeError` if `init()` has not been called:

```python
if _state.tracer is None:
    raise RuntimeError(
        "pixie.instrumentation.init() must be called before observe()"
    )
```

This is undesirable. Application code that uses `start_observation()` or `@observe` should work identically whether or not tracing is set up. The instrumentation should be transparent — a missing `init()` simply means no spans are captured, not that the application crashes.

### Behavior change

When `init()` has not been called (i.e. `_state.tracer is None`):

1. `start_observation()` yields a **no-op `ObservationContext`** — `set_output()` and `set_metadata()` silently do nothing, and no span is submitted to any queue.
2. The `@observe` decorator (section 4) calls the wrapped function normally and returns its result — no span is created.
3. `add_handler()` and `remove_handler()` continue to raise `RuntimeError` — these are explicit setup calls that indicate a programmer error if `init()` hasn't been called.
4. `flush()` continues to return `True` — no-op is already the current behavior.

### Implementation: `_NoOpObservationContext`

Add a lightweight no-op class in `pixie/instrumentation/context.py`:

```python
class _NoOpObservationContext(ObservationContext):
    """No-op observation context used when tracing is not initialized.

    All mutator methods are silent no-ops. No OTel span is created,
    no ObserveSpan is submitted.
    """

    def __init__(self) -> None:
        # Do NOT call super().__init__() — no OTel span exists
        self._input: Any = None
        self._output: Any = None
        self._metadata: dict[str, Any] = {}
        self._error: str | None = None

    def set_output(self, value: Any) -> None:
        pass  # silent no-op

    def set_metadata(self, key: str, value: Any) -> None:
        pass  # silent no-op

    def _snapshot(self) -> None:  # type: ignore[override]
        return None  # no span to produce
```

**Design note:** `_NoOpObservationContext` extends `ObservationContext` so that type checkers see a consistent type from the context manager. It overrides all methods to be no-ops and does not require an OTel span.

### Implementation: updated `start_observation()`

```python
@contextmanager
def start_observation(
    *,
    input: JsonValue,
    name: str | None = None,
) -> Generator[ObservationContext, None, None]:
    """Context manager that creates an OTel span and yields a mutable ObservationContext.

    If init() has not been called, yields a no-op context — the wrapped code
    executes normally but no span is captured.
    """
    if _state.tracer is None:
        yield _NoOpObservationContext()
        return

    tracer = _state.tracer
    span_name = name or "observe"
    with tracer.start_as_current_span(span_name) as otel_span:
        ctx = ObservationContext(otel_span=otel_span, input=input)
        try:
            yield ctx
        except Exception as e:
            ctx._error = type(e).__name__
            raise
        finally:
            observe_span = ctx._snapshot()
            if _state.delivery_queue is not None:
                _state.delivery_queue.submit(observe_span)
```

### Tests

#### `test_context.py` additions

```python
class TestNoOpContext:
    """Tests for no-op behavior when init() has not been called."""

    def test_start_observation_without_init_yields_noop(self) -> None:
        """start_observation() should not raise when init() not called."""
        # Do NOT call px.init()
        with px.start_observation(input="hello") as observation:
            observation.set_output("world")
            observation.set_metadata("key", "value")
        # No error, no span captured — just a no-op

    def test_noop_context_set_output_is_silent(self) -> None:
        with px.start_observation(input="q") as observation:
            observation.set_output("a")
        # No crash, no side effects

    def test_noop_context_set_metadata_is_silent(self) -> None:
        with px.start_observation(input="q") as observation:
            observation.set_metadata("k", "v")
        # No crash, no side effects

    def test_noop_context_exception_still_propagates(self) -> None:
        """Exceptions inside the block should still propagate normally."""
        with pytest.raises(ValueError, match="boom"):
            with px.start_observation(input="q"):
                raise ValueError("boom")

    def test_noop_does_not_submit_to_queue(self) -> None:
        """No span should be submitted when tracing is not initialized."""
        with px.start_observation(input="q") as observation:
            observation.set_output("a")
        # State has no delivery queue — nothing to check, just no crash
```

#### Update existing tests

Remove or update tests that assert `RuntimeError` from `start_observation()` when `init()` is not called — this is no longer the expected behavior.

---

## 4. `@observe` Decorator

### Motivation

`start_observation()` is explicit but verbose for the common case of "capture this function's input and output":

```python
def answer_question(query: str, context: dict) -> str:
    with px.start_observation(input={"query": query, "context": context}, name="answer_question") as observation:
        result = _do_work(query, context)
        observation.set_output(result)
        return result
```

The `@observe` decorator automates this pattern:

```python
@observe()
def answer_question(query: str, context: dict) -> str:
    return _do_work(query, context)
```

### Signature

```python
def observe(
    name: str | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that wraps a function in a start_observation() block.

    Automatically captures function kwargs as input and the return value as output.
    Uses jsonpickle for serialization of both input and output to JsonValue-compatible
    representations.

    Args:
        name: Optional span name. Defaults to the decorated function's ``__name__``.
    """
```

### File: `pixie/instrumentation/observe.py`

```python
"""@observe decorator for automatic function input/output capture."""

from __future__ import annotations

import asyncio
import functools
import inspect
from typing import Any, Callable, TypeVar, ParamSpec

import jsonpickle
from pydantic import JsonValue

from . import start_observation

P = ParamSpec("P")
T = TypeVar("T")


def _serialize(value: Any) -> JsonValue:
    """Serialize a value to a JSON-compatible representation using jsonpickle."""
    return jsonpickle.encode(value, unpicklable=False)


def observe(
    name: str | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that wraps a function in a start_observation() block.

    Automatically captures the function's keyword arguments as input and
    the return value as output. Uses jsonpickle for serialization.

    If tracing is not initialized, the function executes normally with no
    overhead beyond the decorator call itself.

    Args:
        name: Optional span name. Defaults to the function's __name__.
    """
    def decorator(fn: Callable[P, T]) -> Callable[P, T]:
        span_name = name or fn.__name__

        if asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                sig = inspect.signature(fn)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                serialized_input = _serialize(dict(bound.arguments))

                with start_observation(input=serialized_input, name=span_name) as observation:
                    result = await fn(*args, **kwargs)
                    observation.set_output(_serialize(result))
                    return result

            return async_wrapper  # type: ignore[return-value]
        else:
            @functools.wraps(fn)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                sig = inspect.signature(fn)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                serialized_input = _serialize(dict(bound.arguments))

                with start_observation(input=serialized_input, name=span_name) as observation:
                    result = fn(*args, **kwargs)
                    observation.set_output(_serialize(result))
                    return result

            return sync_wrapper  # type: ignore[return-value]

    return decorator
```

### Behavior

1. **Input capture**: Bind all positional and keyword arguments using `inspect.signature`, serialize the resulting dict with `jsonpickle.encode(value, unpicklable=False)`.
2. **Output capture**: Serialize the return value the same way.
3. **Name**: Defaults to `fn.__name__` if not provided.
4. **Async support**: Detects async functions via `asyncio.iscoroutinefunction()` and produces an async wrapper.
5. **No-op when uninitialized**: Since `start_observation()` is already no-op when `init()` hasn't been called (section 3), the decorator transparently does nothing beyond the function call itself.
6. **Exception handling**: If the decorated function raises, the exception propagates normally. The `start_observation()` context manager handles setting the `error` field on the observation.

### Serialization with `jsonpickle`

`jsonpickle` is chosen because it handles arbitrary Python objects (dataclasses, custom classes, nested structures) without requiring the user to define custom serializers. `unpicklable=False` produces clean JSON without type metadata, matching the `JsonValue` type.

```python
import jsonpickle

# Simple types pass through
jsonpickle.encode("hello", unpicklable=False)  # '"hello"'
jsonpickle.encode(42, unpicklable=False)        # '42'

# Complex types are serialized to JSON-friendly dicts
jsonpickle.encode({"query": "hello", "docs": [Doc(id=1)]}, unpicklable=False)
# '{"query": "hello", "docs": [{"id": 1}]}'
```

### Dependency

Add `jsonpickle` as a runtime dependency:

```toml
# pyproject.toml (addition)
dependencies = [
    ...
    "jsonpickle>=4.0.0",
]
```

### Export

Add `observe` to the public API in `pixie/instrumentation/__init__.py`:

```python
from .observe import observe

__all__ = [
    ...
    "observe",
    ...
]
```

### Usage examples

#### Basic sync function

```python
import pixie.instrumentation as px

px.init()
px.add_handler(my_handler)

@px.observe()
def answer_question(query: str, context: list[str]) -> str:
    # LLM calls here are automatically parented to this observation
    return llm_call(query, context)

result = answer_question("What is 2+2?", ["math facts"])
# ObserveSpan produced with:
#   name = "answer_question"
#   input = '{"query": "What is 2+2?", "context": ["math facts"]}'
#   output = '"4"'
```

#### Async function

```python
@px.observe(name="generate_response")
async def generate(prompt: str, max_tokens: int = 512) -> str:
    response = await client.messages.create(...)
    return response.content[0].text

await generate("hello")
# ObserveSpan with name="generate_response"
```

#### Without init — no-op

```python
# No px.init() called

@px.observe()
def my_function(x: int) -> int:
    return x * 2

result = my_function(21)
assert result == 42  # function works normally, no span captured
```

#### Nested with start_observation

```python
@px.observe()
def process_request(query: str) -> str:
    with px.start_observation(input=query, name="retrieval") as observation:
        docs = retrieve(query)
        observation.set_output(docs)
    return summarize(query, docs)

# Produces two observations:
# 1. "process_request" (root, from @observe)
# 2. "retrieval" (child, from start_observation, parented to process_request)
```

---

## Dependencies

### New runtime dependency

```toml
# pyproject.toml
dependencies = [
    ...
    "jsonpickle>=4.0.0",
]
```

---

## File Structure (additions / changes)

```
pixie/
  instrumentation/
    __init__.py            # UPDATE: no-op behavior, export observe, update docstrings
    context.py             # UPDATE: add _NoOpObservationContext
    observe.py             # NEW: @observe decorator

tests/
  pixie/
    instrumentation/
      test_context.py      # UPDATE: no-op tests, span→observation, input required
      test_observe.py      # NEW: @observe decorator tests
      test_integration.py  # UPDATE: span→observation naming

specs/
  manual-instrumentation-usability.md   # this file
```

---

## Tests

### `test_context.py` updates

- **Remove**: tests asserting `RuntimeError` from `start_observation()` when `init()` not called
- **Add**: `TestNoOpContext` class (see section 3)
- **Update**: all `as span:` to `as observation:`
- **Update**: add `input=...` where currently omitted

### `test_observe.py` (new)

```python
class TestObserveDecorator:
    """Tests for the @observe decorator."""

    def test_sync_function_captured(self, recording_handler: RecordingHandler) -> None:
        """@observe captures sync function input and output as an ObserveSpan."""
        px.init()
        px.add_handler(recording_handler)

        @observe()
        def greet(name: str) -> str:
            return f"Hello, {name}!"

        result = greet("Alice")
        px.flush()

        assert result == "Hello, Alice!"
        assert len(recording_handler.observe_spans) == 1
        obs = recording_handler.observe_spans[0]
        assert obs.name == "greet"
        assert '"name": "Alice"' in obs.input or '"name":"Alice"' in obs.input
        assert "Hello, Alice!" in obs.output

    async def test_async_function_captured(
        self, recording_handler: RecordingHandler
    ) -> None:
        """@observe captures async function input and output."""
        px.init()
        px.add_handler(recording_handler)

        @observe()
        async def greet(name: str) -> str:
            return f"Hello, {name}!"

        result = await greet("Bob")
        px.flush()

        assert result == "Hello, Bob!"
        assert len(recording_handler.observe_spans) == 1
        obs = recording_handler.observe_spans[0]
        assert obs.name == "greet"

    def test_custom_name(self, recording_handler: RecordingHandler) -> None:
        """@observe(name=...) uses the custom name."""
        px.init()
        px.add_handler(recording_handler)

        @observe(name="custom_op")
        def work(x: int) -> int:
            return x * 2

        work(5)
        px.flush()

        obs = recording_handler.observe_spans[0]
        assert obs.name == "custom_op"

    def test_default_name_is_function_name(
        self, recording_handler: RecordingHandler
    ) -> None:
        """@observe() without name uses fn.__name__."""
        px.init()
        px.add_handler(recording_handler)

        @observe()
        def my_special_fn(x: int) -> int:
            return x

        my_special_fn(1)
        px.flush()

        obs = recording_handler.observe_spans[0]
        assert obs.name == "my_special_fn"

    def test_exception_propagates(
        self, recording_handler: RecordingHandler
    ) -> None:
        """Exceptions from the decorated function propagate and set error field."""
        px.init()
        px.add_handler(recording_handler)

        @observe()
        def boom() -> None:
            raise ValueError("kaboom")

        with pytest.raises(ValueError, match="kaboom"):
            boom()

        px.flush()
        obs = recording_handler.observe_spans[0]
        assert obs.error == "ValueError"

    def test_noop_without_init(self) -> None:
        """@observe works normally when init() has not been called."""
        # Do NOT call px.init()
        @observe()
        def double(x: int) -> int:
            return x * 2

        assert double(21) == 42

    def test_complex_input_serialized(
        self, recording_handler: RecordingHandler
    ) -> None:
        """Complex input types are serialized via jsonpickle."""
        px.init()
        px.add_handler(recording_handler)

        @observe()
        def process(data: dict, items: list) -> str:
            return "done"

        process({"key": "value"}, [1, 2, 3])
        px.flush()

        obs = recording_handler.observe_spans[0]
        # Input should be a JSON string containing the function arguments
        assert "key" in obs.input
        assert "value" in obs.input

    def test_positional_args_captured(
        self, recording_handler: RecordingHandler
    ) -> None:
        """Positional arguments are captured by binding to the signature."""
        px.init()
        px.add_handler(recording_handler)

        @observe()
        def add(a: int, b: int) -> int:
            return a + b

        result = add(3, 4)
        px.flush()

        assert result == 7
        obs = recording_handler.observe_spans[0]
        # Both positional args should appear in the serialized input
        assert "a" in obs.input
        assert "b" in obs.input
```

### `test_integration.py` updates

- **Update**: all `as span:` to `as observation:`
- **Update**: docstrings referencing `log()` to `start_observation()`

### `test_eval_utils.py` / `test_trace_capture.py` updates

- **Update**: all `as span:` to `as observation:`

---

## Migration Notes

### Breaking changes

| Change                                               | Impact                                                 | Migration                                             |
| ---------------------------------------------------- | ------------------------------------------------------ | ----------------------------------------------------- |
| `input` is now **required** in `start_observation()` | Call sites that omitted `input` will get a `TypeError` | Add `input=None` or `input=<value>` to all call sites |

### Non-breaking changes

| Change                                                    | Impact                                                                               |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `start_observation()` no longer raises when uninitialized | Code that caught `RuntimeError` from `start_observation()` can remove the try/except |
| `@observe` decorator added                                | New API, no existing code affected                                                   |
| `span` → `observation` variable rename                    | Convention only, not enforced by the API                                             |

---

## Example Usage (Updated)

```python
import pixie.instrumentation as px
from pixie.instrumentation import InstrumentationHandler, LLMSpan, ObserveSpan

class MyHandler(InstrumentationHandler):

    async def on_llm(self, span: LLMSpan) -> None:
        await db.insert_async("llm_spans", {
            "span_id": span.span_id,
            "model": span.request_model,
            "input_tokens": span.input_tokens,
        })

    async def on_observe(self, span: ObserveSpan) -> None:
        await db.insert_async("observe_spans", {
            "span_id": span.span_id,
            "input": span.input,
            "output": span.output,
        })

px.init(capture_content=True)
px.add_handler(MyHandler())

# ── Using start_observation (explicit) ──

from anthropic import Anthropic
client = Anthropic()

with px.start_observation(input=user_query, name="answer_question") as observation:
    docs = retriever.get(user_query)
    observation.set_metadata("retrieved_docs", docs)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": user_query}],
    )
    answer = response.content[0].text
    observation.set_output(answer)

# ── Using @observe (automatic) ──

@px.observe()
def answer_question(query: str) -> str:
    docs = retriever.get(query)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": query}],
    )
    return response.content[0].text

answer = answer_question("What is the capital of France?")

# ── Works without init (no-op) ──

# If px.init() was never called, both patterns work silently:
with px.start_observation(input="q") as observation:
    observation.set_output("a")  # no-op, no span captured

@px.observe()
def safe_function(x: int) -> int:
    return x * 2

safe_function(21)  # returns 42, no span captured

import atexit
atexit.register(px.flush)
```

---

## Out of Scope

- Changes to `LLMSpanProcessor` or `_DeliveryQueue` internals
- Changes to `InstrumentationHandler` interface
- Changes to `add_handler()` / `remove_handler()` behavior (they still raise when uninitialized)
- Storage, eval harness, or autoevals adapter changes
- OTel metrics pipeline
