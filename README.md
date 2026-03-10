# pixie-qa

Automated quality assurance for AI applications.

This repository currently provides the `pixie.instrumentation` package, which adds:

- Typed `LLMSpan` capture from OpenInference / OpenTelemetry spans
- A `log()` context manager that emits typed `ObserveSpan` data
- Parent/child trace linkage between observed blocks and nested LLM calls
- Background, non-blocking delivery to a user-defined handler

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

## Public API

- `init(handler, *, capture_content=False, queue_size=1000)`
- `log(input=None, *, name=None)`
- `flush(timeout_seconds=5.0)`

Data model types are exported from `pixie.instrumentation`, including `LLMSpan`, `ObserveSpan`, and message/content/tool types.

## Development

Run checks through `uv run`:

```bash
uv run pytest
uv run mypy pixie/
uv run ruff check .
```

Run instrumentation-only tests:

```bash
uv run pytest tests/pixie/instrumentation -v
```

## Documentation

- Implementation spec: `specs/instrumentation.md`
- Change history: `changelogs/`

## Dev Setup (Skills)

```bash
npx openskills install anthropics/skills
```
