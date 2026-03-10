# Pixie Instrumentation Library — Implementation Spec

## Overview

`pixie.instrumentation` is a lightweight Python sub-package that:

1. Wraps LLM provider calls using **OpenInference** and delivers typed `LLMSpan` objects to a handler.
2. Provides a `log()` context manager for wrapping arbitrary code blocks into `ObserveSpan` objects, carrying user-defined inputs, outputs, and metadata.
3. Associates the two via standard OTel trace context: LLM calls made _inside_ a `log()` block are children in the same trace, so `LLMSpan.parent_span_id == ObserveSpan.span_id`.

Users call `pixie.instrumentation.init(handler)` once at startup.

---

## Implementation Status (2026-03-09)

Status: Implemented.

The module and test suite described in this spec are present in the repository:

- Source package: `pixie/instrumentation/`
- Tests: `tests/pixie/instrumentation/`
- Package/dependency config: `pyproject.toml`, `uv.lock`

Validation snapshot at delivery time:

- `uv run pytest tests/ -v` → passing
- `uv run mypy pixie/` → passing
- `uv run ruff check .` → passing

---

## Package Structure

```
pixie/
└── instrumentation/
    ├── __init__.py        # public API: init(), log()
    ├── spans.py           # ObserveSpan, LLMSpan, and all message/content types
    ├── handler.py         # InstrumentationHandler abstract base class
    ├── context.py         # _SpanContext — the mutable object yielded by log()
    ├── processor.py       # LLMSpanProcessor (OpenInference span attrs → LLMSpan)
    ├── queue.py           # _DeliveryQueue (background worker thread)
    ├── instrumentors.py   # auto-discovers and activates OpenInference instrumentors
    └── py.typed
```

---

## Dependencies

```toml
[project]
name = "pixie"
requires-python = ">=3.10"

dependencies = [
    "opentelemetry-sdk>=1.27.0",
    "opentelemetry-api>=1.27.0",
    "openinference-instrumentation>=0.1.44",
]

[project.optional-dependencies]
openai     = ["openinference-instrumentation-openai"]
anthropic  = ["openinference-instrumentation-anthropic"]
langchain  = ["openinference-instrumentation-langchain"]
google     = ["openinference-instrumentation-google-genai"]
dspy       = ["openinference-instrumentation-dspy"]
all        = [
    "openinference-instrumentation-openai",
    "openinference-instrumentation-anthropic",
    "openinference-instrumentation-langchain",
    "openinference-instrumentation-google-genai",
    "openinference-instrumentation-dspy",
]
```

---

## Data Model (`pixie/instrumentation/spans.py`)

### Message content types

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Any


@dataclass(frozen=True)
class TextContent:
    text: str
    type: Literal["text"] = "text"


@dataclass(frozen=True)
class ImageContent:
    url: str                           # https:// or data: URI
    detail: str | None = None          # "low" | "high" | "auto" | None
    type: Literal["image"] = "image"


MessageContent = TextContent | ImageContent
```

### Tool types

```python
@dataclass(frozen=True)
class ToolCall:
    """Tool invocation requested by the model."""
    name: str
    arguments: dict                    # always deserialized, never a raw JSON string
    id: str | None = None


@dataclass(frozen=True)
class ToolDefinition:
    """Tool made available to the model in the request."""
    name: str
    description: str | None = None
    parameters: dict | None = None     # JSON Schema object
```

### Message types

```python
@dataclass(frozen=True)
class SystemMessage:
    content: str
    role: Literal["system"] = "system"


@dataclass(frozen=True)
class UserMessage:
    content: tuple[MessageContent, ...]
    role: Literal["user"] = "user"

    @classmethod
    def from_text(cls, text: str) -> "UserMessage":
        return cls(content=(TextContent(text=text),))


@dataclass(frozen=True)
class AssistantMessage:
    content: tuple[MessageContent, ...]
    tool_calls: tuple[ToolCall, ...]
    finish_reason: str | None = None
    role: Literal["assistant"] = "assistant"


@dataclass(frozen=True)
class ToolResultMessage:
    content: str
    tool_call_id: str | None = None
    tool_name: str | None = None
    role: Literal["tool"] = "tool"


Message = SystemMessage | UserMessage | AssistantMessage | ToolResultMessage
```

### `LLMSpan` — one LLM provider call

Produced by the `LLMSpanProcessor` from OpenInference span attributes.

```python
@dataclass(frozen=True)
class LLMSpan:
    # ── Identity ──────────────────────────────────────────────────────────────
    span_id: str                              # hex, 16 chars
    trace_id: str                             # hex, 32 chars
    parent_span_id: str | None                # links to ObserveSpan.span_id when nested

    # ── Timing ────────────────────────────────────────────────────────────────
    started_at: datetime
    ended_at: datetime
    duration_ms: float

    # ── Provider / model ──────────────────────────────────────────────────────
    operation: str                            # "chat" | "embedding"
    provider: str                             # "openai" | "anthropic" | "google" | ...
    request_model: str
    response_model: str | None

    # ── Token usage ───────────────────────────────────────────────────────────
    input_tokens: int                         # default 0
    output_tokens: int                        # default 0
    cache_read_tokens: int                    # default 0
    cache_creation_tokens: int                # default 0

    # ── Request parameters ─────────────────────────────────────────────────────
    request_temperature: float | None
    request_max_tokens: int | None
    request_top_p: float | None

    # ── Response metadata ──────────────────────────────────────────────────────
    finish_reasons: tuple[str, ...]           # default ()
    response_id: str | None
    output_type: str | None                   # "json" | "text" | None
    error_type: str | None

    # ── Content (populated when capture_content=True) ─────────────────────────
    input_messages: tuple[Message, ...]       # default ()
    output_messages: tuple[AssistantMessage, ...]  # default ()
    tool_definitions: tuple[ToolDefinition, ...]   # always populated when available
```

### `ObserveSpan` — a user-defined instrumented block

Produced when a `log()` context manager block exits.

```python
@dataclass(frozen=True)
class ObserveSpan:
    # ── Identity ──────────────────────────────────────────────────────────────
    span_id: str                              # hex, 16 chars
    trace_id: str                             # hex, 32 chars
    parent_span_id: str | None

    # ── Timing ────────────────────────────────────────────────────────────────
    started_at: datetime
    ended_at: datetime
    duration_ms: float

    # ── User-defined fields ───────────────────────────────────────────────────
    name: str | None                          # optional label for the block
    input: Any                                # value passed to log(input=...)
    output: Any                               # value set via span.set_output(...)
    metadata: dict                            # accumulated via span.set_metadata(k, v)
    error: str | None                         # exception type if block raised, else None
```

---

## Public API (`pixie/instrumentation/__init__.py`)

### `init(*, capture_content=False, queue_size=1000)`

Initializes the instrumentation sub-package. Truly idempotent — calling `init()` a second time is a no-op.

**Parameters:**

- `capture_content: bool` — sets `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`, enabling `input_messages` / `output_messages` on `LLMSpan`
- `queue_size: int` — shared delivery queue depth, default 1000

**Behavior:**

1. Return immediately if already initialized (idempotent)
2. Set env vars before instrumentors load
3. Create `_HandlerRegistry` and `_DeliveryQueue(registry, queue_size)`
4. Set up `TracerProvider` with `LLMSpanProcessor(delivery_queue)`
5. Store a module-level `_tracer` from this provider for use by `log()`
6. Set as global tracer provider
7. Call `_activate_instrumentors()`

Handler registration is separate — see `add_handler()` and `remove_handler()`.

### `add_handler(handler)`

Register _handler_ to receive span notifications. Must be called after `init()`. Multiple handlers can be registered; each receives every span delivered through the pipeline.

### `remove_handler(handler)`

Unregister a previously registered _handler_. Raises `ValueError` if the handler was not registered.

### `_HandlerRegistry` (`pixie/instrumentation/handler.py`)

Internal fan-out handler that dispatches to all registered handlers. Thread-safe — handlers can be added/removed from any thread while the delivery worker dispatches from the background thread. Per-handler exceptions are caught via `contextlib.suppress(Exception)` so one failing handler does not prevent delivery to the remaining handlers.

---

### `log(input=None, *, name=None) -> contextmanager[_SpanContext]`

Context manager. Creates an OTel span, yields a mutable `_SpanContext`, and on exit snapshots it into an `ObserveSpan` delivered to the handler.

```python
@contextmanager
def log(input: Any = None, *, name: str | None = None):
    tracer = _state.tracer
    span_name = name or "observe"
    with tracer.start_as_current_span(span_name) as otel_span:
        ctx = _SpanContext(otel_span=otel_span, input=input)
        try:
            yield ctx
        except Exception as e:
            ctx._error = type(e).__name__
            raise
        finally:
            observe_span = ctx._snapshot()
            _state.delivery_queue.submit(observe_span)
```

`_SpanContext` is the mutable object users interact with inside the block. It is never delivered directly — `_snapshot()` produces the final frozen `ObserveSpan`.

The OTel span created here becomes the **parent** of any LLM spans initiated inside the block, so `LLMSpan.parent_span_id == ObserveSpan.span_id` naturally via OTel context propagation.

---

## `_SpanContext` (`pixie/instrumentation/context.py`)

The mutable object yielded by `log()`. Users interact with this inside the `with` block.

```python
class _SpanContext:
    def __init__(self, otel_span, input: Any):
        self._otel_span = otel_span
        self._input = input
        self._output: Any = None
        self._metadata: dict = {}
        self._error: str | None = None

    def set_output(self, value: Any) -> None:
        """Set the output value for this observed block."""
        self._output = value

    def set_metadata(self, key: str, value: Any) -> None:
        """Accumulate a metadata key-value pair."""
        self._metadata[key] = value

    def _snapshot(self) -> ObserveSpan:
        ctx = self._otel_span.get_span_context()
        start_ns = self._otel_span.start_time
        end_ns = self._otel_span.end_time
        return ObserveSpan(
            span_id=format(ctx.span_id, "016x"),
            trace_id=format(ctx.trace_id, "032x"),
            parent_span_id=_extract_parent_span_id(self._otel_span),
            started_at=datetime.fromtimestamp(start_ns / 1e9, tz=timezone.utc),
            ended_at=datetime.fromtimestamp(end_ns / 1e9, tz=timezone.utc),
            duration_ms=(end_ns - start_ns) / 1e6,
            name=self._otel_span.name,
            input=self._input,
            output=self._output,
            metadata=dict(self._metadata),
            error=self._error,
        )
```

**Design note:** `_SpanContext` is intentionally not exported. Users only need to know about `set_output()` and `set_metadata()`. The frozen `ObserveSpan` delivered to the handler is the public type.

---

## `InstrumentationHandler` (`pixie/instrumentation/handler.py`)

```python
from abc import ABC, abstractmethod
from .spans import LLMSpan, ObserveSpan

class InstrumentationHandler(ABC):

    def on_llm(self, span: LLMSpan) -> None:
        """Called on background thread when an LLM provider call completes.
        Default: no-op. Override to capture LLM call data for root-cause analysis.
        Exceptions are caught and suppressed.
        """
        pass

    def on_observe(self, span: ObserveSpan) -> None:
        """Called on background thread when a log() block completes.
        Default: no-op. Override to capture eval-relevant data.
        Exceptions are caught and suppressed.
        """
        pass
```

Both methods are optional overrides, not abstract — a handler only implementing `on_llm` is valid, and vice versa.

**Association pattern:** LLM calls made inside a `log()` block will have `llm_span.parent_span_id == observe_span.span_id` and the same `trace_id`. Join in storage on these keys.

---

## `LLMSpanProcessor` (`pixie/instrumentation/processor.py`)

Implements `opentelemetry.sdk.trace.SpanProcessor`. Only `on_end` is implemented.

### Detection

Return immediately unless `span.attributes.get("openinference.span.kind") == "LLM"`.

Entire `on_end` body wrapped in try/except — never raises.

### Attribute mappings

**Identity / timing:**

```
span_id        ← format(span.context.span_id, "016x")
trace_id       ← format(span.context.trace_id, "032x")
parent_span_id ← format(span.parent.span_id, "016x") if span.parent else None
started_at     ← datetime.fromtimestamp(span.start_time / 1e9, tz=timezone.utc)
ended_at       ← datetime.fromtimestamp(span.end_time / 1e9, tz=timezone.utc)
duration_ms    ← (span.end_time - span.start_time) / 1e6
```

**Provider / model:**

```
request_model  ← attrs.get("llm.model_name") or attrs.get("gen_ai.request.model", "")
response_model ← attrs.get("gen_ai.response.model")
provider       ← attrs.get("gen_ai.system") or _infer_provider(request_model)
operation      ← "chat" for LLM spans, "embedding" for EMBEDDING spans
```

**Token usage:**

```
input_tokens          ← attrs.get("llm.token_count.prompt", 0)
output_tokens         ← attrs.get("llm.token_count.completion", 0)
cache_read_tokens     ← attrs.get("llm.token_count.cache_read", 0)
cache_creation_tokens ← attrs.get("llm.token_count.cache_creation", 0)
```

**Request params** — parsed from `llm.invocation_parameters` JSON string:

```python
params = json.loads(attrs.get("llm.invocation_parameters", "{}"))
request_temperature ← params.get("temperature")
request_max_tokens  ← params.get("max_tokens") or params.get("max_completion_tokens")
request_top_p       ← params.get("top_p")
```

**Response / error:**

```
response_id    ← attrs.get("llm.response_id") or attrs.get("gen_ai.response.id")
output_type    ← attrs.get("gen_ai.output.type")
error_type     ← attrs.get("error.type")
               or ("error" if span.status.status_code == StatusCode.ERROR else None)
finish_reasons ← collected from output message finish_reason fields (see parsing below)
```

### Input message parsing

OpenInference uses indexed flat span attributes. Iterate `i = 0, 1, ...` until role key absent:

```
llm.input_messages.{i}.message.role
llm.input_messages.{i}.message.content                          ← plain text fallback
llm.input_messages.{i}.message.contents.{j}.message_content.type
llm.input_messages.{i}.message.contents.{j}.message_content.text
llm.input_messages.{i}.message.contents.{j}.message_content.image.url.url
llm.input_messages.{i}.message.contents.{j}.message_content.image.url.detail
llm.input_messages.{i}.message.tool_call_id                     ← role="tool"
llm.input_messages.{i}.message.name                             ← role="tool"
llm.input_messages.{i}.message.tool_calls.{j}.tool_call.function.name
llm.input_messages.{i}.message.tool_calls.{j}.tool_call.function.arguments
llm.input_messages.{i}.message.tool_calls.{j}.tool_call.id
```

Role → type mapping:

- `"system"` → `SystemMessage`
- `"user"` → `UserMessage` (parse content parts)
- `"assistant"` → `AssistantMessage` (parse content parts + tool calls)
- `"tool"` → `ToolResultMessage`

Content parts: try `contents.{j}` multimodal structure first; fall back to plain `.content` string as `TextContent`.

Tool call arguments: always `json.loads()` if string; on `JSONDecodeError` store `{"_raw": raw_string}`.

### Output message parsing

Same structure under `llm.output_messages.{i}`. Always `AssistantMessage`. Collect `finish_reason` per message into `LLMSpan.finish_reasons`.

### Tool definition parsing

```
llm.tools.{i}.tool.name
llm.tools.{i}.tool.description
llm.tools.{i}.tool.json_schema      ← JSON string → dict
```

Produces `tuple[ToolDefinition, ...]`. Always populated when available, independent of `capture_content`.

---

## `_DeliveryQueue` (`pixie/instrumentation/queue.py`)

Single queue for both `LLMSpan` and `ObserveSpan`. The handler methods are dispatched by type.

```python
class _DeliveryQueue:
    def __init__(self, handler: InstrumentationHandler, maxsize: int = 1000):
        self._handler = handler
        self._queue: queue.Queue[LLMSpan | ObserveSpan] = queue.Queue(maxsize=maxsize)
        self._dropped_count = 0
        self._thread = threading.Thread(
            target=self._worker, daemon=True, name="pixie-delivery-worker"
        )
        self._thread.start()

    def submit(self, item: LLMSpan | ObserveSpan) -> None:
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            self._dropped_count += 1

    def flush(self, timeout_seconds: float = 5.0) -> bool:
        try:
            self._queue.join()
            return True
        except Exception:
            return False

    def _worker(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if isinstance(item, LLMSpan):
                    self._handler.on_llm(item)
                elif isinstance(item, ObserveSpan):
                    self._handler.on_observe(item)
            except Exception:
                pass
            finally:
                self._queue.task_done()

    @property
    def dropped_count(self) -> int:
        return self._dropped_count
```

---

## `_activate_instrumentors` (`pixie/instrumentation/instrumentors.py`)

```python
_KNOWN_INSTRUMENTORS = [
    ("openinference.instrumentation.openai",       "OpenAIInstrumentor"),
    ("openinference.instrumentation.anthropic",    "AnthropicInstrumentor"),
    ("openinference.instrumentation.langchain",    "LangChainInstrumentor"),
    ("openinference.instrumentation.google_genai", "GoogleGenAIInstrumentor"),
    ("openinference.instrumentation.dspy",         "DSPyInstrumentor"),
    # OTel official OpenAI v2 as secondary fallback
    ("opentelemetry.instrumentation.openai_v2",    "OpenAIInstrumentor"),
]

def _activate_instrumentors() -> list[str]:
    activated = []
    for module_path, class_name in _KNOWN_INSTRUMENTORS:
        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            cls().instrument()
            activated.append(class_name)
        except ImportError:
            pass
        except Exception:
            pass
    return activated
```

---

## Global State

```python
@dataclass
class _State:
    registry: _HandlerRegistry | None = None
    delivery_queue: _DeliveryQueue | None = None
    tracer: Tracer | None = None
    tracer_provider: TracerProvider | None = None
    initialized: bool = False

_state = _State()
```

`init()` is truly idempotent — a second call is a no-op. Handler registration is managed separately via `add_handler()` / `remove_handler()`. A `_reset_state()` helper exists for test isolation (not part of the public API).

---

## Error Handling Rules

1. Never raise from `LLMSpanProcessor.on_end()` — entire body in try/except
2. Never raise from `_DeliveryQueue._worker()` — each iteration wrapped
3. Never raise from `submit()` — drop silently on full queue
4. Handler method exceptions silently swallowed
5. Malformed JSON in span attributes — fall back to `{}` or `None`, never raise
6. `log()` block exceptions re-raised normally after snapshotting `error` field

---

## Tests

### `test_spans.py`

- `ObserveSpan` and `LLMSpan` are frozen (mutation raises)
- `UserMessage.from_text("hello")` produces `(TextContent(text="hello"),)`
- `ToolCall.arguments` is always a dict

### `test_context.py`

- `set_output()` and `set_metadata()` update state correctly
- `_snapshot()` produces correct frozen `ObserveSpan`
- Exception inside `with` block → `error` field set, exception re-raised
- Nesting: `log()` inside `log()` → inner `parent_span_id` == outer `span_id`

### `test_queue.py`

- Both `LLMSpan` and `ObserveSpan` dispatched to correct handler methods
- Drop on full queue; `dropped_count` increments
- Handler exceptions don't crash worker

### `test_processor.py`

- Non-LLM spans ignored
- Basic text conversation → correct typed messages
- Tool call in output → `AssistantMessage.tool_calls` populated
- Tool result in input → `ToolResultMessage` with correct fields
- Tool definitions → `ToolDefinition` with deserialized `parameters`
- `llm.invocation_parameters` parsed into temperature/max_tokens/top_p
- `finish_reasons` populated from output messages

### `test_integration.py`

- `init()` + `add_handler(handler)` → fake LLM span → `on_llm()` called with correct `LLMSpan`
- `log(input=...)` block → `on_observe()` called with correct `ObserveSpan`
- LLM call inside `log()` block → `llm_span.parent_span_id == observe_span.span_id`
- `flush()` → all pending spans delivered before flush returns
- Multiple handlers: `add_handler(h1)` + `add_handler(h2)` → both receive every span
- `remove_handler(h1)` → h1 no longer receives spans, h2 still does

---

## Example Usage

```python
import pixie.instrumentation as px
from pixie.instrumentation import InstrumentationHandler, LLMSpan, ObserveSpan

class MyHandler(InstrumentationHandler):

    def on_llm(self, span: LLMSpan) -> None:
        # Root-cause data — store for debugging when evals flag issues
        db.insert("llm_spans", {
            "span_id": span.span_id,
            "parent_span_id": span.parent_span_id,
            "trace_id": span.trace_id,
            "model": span.request_model,
            "input_tokens": span.input_tokens,
            "output_tokens": span.output_tokens,
            "latency_ms": span.duration_ms,
        })

    def on_observe(self, span: ObserveSpan) -> None:
        # Eval data — the input/output/metadata you actually run evals against
        db.insert("observe_spans", {
            "span_id": span.span_id,
            "trace_id": span.trace_id,
            "input": span.input,
            "output": span.output,
            "metadata": span.metadata,
            "error": span.error,
        })

px.init(capture_content=True)
px.add_handler(MyHandler())

# Usage
from anthropic import Anthropic
client = Anthropic()

with px.log(input=user_query, name="answer_question") as span:
    # retrieve context, run the LLM call
    docs = retriever.get(user_query)
    span.set_metadata("retrieved_docs", docs)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": user_query}]
    )
    answer = response.content[0].text
    span.set_output(answer)
    span.set_metadata("retrieval_count", len(docs))

# After the block:
# on_observe() called with ObserveSpan(input=user_query, output=answer, ...)
# on_llm()     called with LLMSpan(parent_span_id=observe_span.span_id, ...)
# Join in DB:  observe_spans.span_id == llm_spans.parent_span_id

import atexit
atexit.register(px.flush)
```

---

## Out of Scope

- Other `pixie.*` sub-packages — this spec covers `pixie.instrumentation` only
- OTel metrics pipeline — traces only
- Async handler interface — background thread handles this; handlers are sync
- Sampling / rate limiting — implement in handler if needed
- Retry logic for failed handler calls — implement in handler if needed
- Any UI, dashboard, or storage backend
