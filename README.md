# pixie-qa

Automated quality assurance for AI applications.

This repository provides:

- **`pixie.instrumentation`** — Typed span capture from OpenInference / OpenTelemetry
- **`pixie.storage`** — Persistence, querying, and tree assembly for observation traces

## Installation

```bash
uv sync
```

Optional provider extras:

```bash
uv sync --extra openai
uv sync --extra anthropic
uv sync --extra langchain
uv sync --extra google
uv sync --extra dspy
```

Install everything:

```bash
uv sync --extra all
```

## Quick Start

### Instrumentation

```python
import pixie.instrumentation as px
from pixie.instrumentation import InstrumentationHandler, LLMSpan, ObserveSpan


class PrintHandler(InstrumentationHandler):
	def on_llm(self, span: LLMSpan) -> None:
		print("LLM", span.request_model, span.duration_ms)

	def on_observe(self, span: ObserveSpan) -> None:
		print("OBS", span.name, span.input, span.output)


px.init(PrintHandler(), capture_content=True)

with px.log(input="What is the capital of France?", name="qa") as span:
	answer = "Paris"
	span.set_output(answer)
	span.set_metadata("source", "demo")

px.flush()
```

### Observation Store

```python
import asyncio
from pixie.storage import (
    ObservationStore,
    build_tree,
    as_evaluable,
)

async def main():
    store = ObservationStore()
    await store.create_tables()

    # Save spans produced by instrumentation
    # await store.save(observe_span)
    # await store.save(llm_span)

    # Query a full trace as a tree
    roots = await store.get_trace("your-trace-id")
    for root in roots:
        print(root.to_text())

    # Eval shortcuts
    root_span = await store.get_root("your-trace-id")
    evaluable = as_evaluable(root_span)
    print(evaluable.eval_input, evaluable.eval_output)

    # Browse traces
    traces = await store.list_traces(limit=10)
    for t in traces:
        print(t["trace_id"], t["root_name"], t["observation_count"])

asyncio.run(main())
```

## Public API

### Instrumentation

- `init(handler, *, capture_content=False, queue_size=1000)`
- `log(input=None, *, name=None)`
- `flush(timeout_seconds=5.0)`

Data model types are exported from `pixie.instrumentation`, including `LLMSpan`, `ObserveSpan`, and message/content/tool types.

### Observation Store

- `ObservationStore(engine=None)` — async store backed by SQLite
  - `create_tables()` — initialize schema
  - `save(span)` / `save_many(spans)` — persist spans
  - `get_trace(trace_id)` — tree of `ObservationNode`
  - `get_trace_flat(trace_id)` — flat ordered list
  - `get_root(trace_id)` — root `ObserveSpan`
  - `get_last_llm(trace_id)` — most recent `LLMSpan`
  - `get_by_name(name)` / `get_by_type(span_kind)` — component queries
  - `get_errors(trace_id=None)` — spans with errors
  - `list_traces(limit, offset)` — trace summaries
- `ObservationNode` — tree wrapper with `find()`, `find_by_type()`, `to_text()`
- `build_tree(spans)` — assemble flat spans into a tree
- `Evaluable` protocol with `ObserveSpanEval`, `LLMSpanEval`, `as_evaluable()`

## Development

Run checks through `uv run`:

```bash
uv run pytest
uv run mypy pixie/
uv run ruff check .
```

Run module-specific tests:

```bash
uv run pytest tests/pixie/instrumentation -v
uv run pytest tests/pixie/observation_store -v
```

## Documentation

- Instrumentation spec: `specs/instrumentation.md`
- Storage spec: `specs/storage.md`
- Change history: `changelogs/`

## Dev Setup (Skills)

```bash
npx openskills install anthropics/skills
```
