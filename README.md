# pixie-qa

Automated quality assurance for AI applications.

This repository provides:

- **`pixie.instrumentation`** — Typed span capture from OpenInference / OpenTelemetry
- **`pixie.storage`** — Persistence, querying, and tree assembly for observation traces
- **`pixie.evals`** — Evaluation harness for LLM application testing
- **`pixie.dataset`** — Named collections of evaluable items (JSON-file-backed CRUD)

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

### One-Line Storage Setup

```python
from pixie import enable_storage

enable_storage()  # creates DB, registers handler — one line, everything works

# Now any instrumented code automatically persists traces to SQLite
```

### Instrumentation

```python
import pixie.instrumentation as px
from pixie.instrumentation import InstrumentationHandler, LLMSpan, ObserveSpan


class PrintHandler(InstrumentationHandler):
	async def on_llm(self, span: LLMSpan) -> None:
		print("LLM", span.request_model, span.duration_ms)

	async def on_observe(self, span: ObserveSpan) -> None:
		print("OBS", span.name, span.input, span.output)


px.init()  # capture_content=True by default
px.add_handler(PrintHandler())

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

- `init(*, capture_content=True, queue_size=1000)` — initialize OTel pipeline (idempotent); content capture on by default
- `add_handler(handler)` — register a handler to receive spans
- `remove_handler(handler)` — unregister a handler
- `log(input=None, *, name=None)` — context manager for observe spans
- `flush(timeout_seconds=5.0)` — drain the delivery queue

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
- `Evaluable` — Pydantic ``BaseModel`` with `eval_input`, `eval_output`, `eval_metadata`, `expected_output`
- `UNSET` sentinel — distinguishes "not set" from `None` for `expected_output`
- `as_evaluable(span)` — convert a span to an `Evaluable`

### Evaluation Harness

```python
from pixie.evals import (
    Evaluation, evaluate, run_and_evaluate, assert_pass,
    capture_traces, MemoryTraceHandler, EvalAssertionError,
    ScoreThreshold, last_llm_call, root,
)
from pixie.storage.evaluable import Evaluable
from pixie.storage.tree import ObservationNode
```

- `Evaluation(score, reasoning, details={})` — frozen result of one evaluator run
- `evaluate(evaluator, evaluable, *, trace=None)` — run one evaluator (sync or async)
- `run_and_evaluate(evaluator, runnable, input, *, from_trace=None)` — run a callable, capture traces, evaluate
- `assert_pass(runnable, inputs, evaluators, *, evaluables=None, passes=1, pass_criteria=None, from_trace=None)` — batch evaluation with pass/fail
- `MemoryTraceHandler` — `InstrumentationHandler` that collects spans in-memory
- `capture_traces()` — context manager that registers a handler and yields it
- `EvalAssertionError` — raised when `assert_pass` fails; carries full results tensor
- `ScoreThreshold(threshold=0.5, pct=1.0)` — configurable pass criteria for `assert_pass`
- `last_llm_call(trace)` — extract the most recent `LLMSpan` from a trace as `Evaluable`
- `root(trace)` — extract the first root span from a trace as `Evaluable`

### Pre-made Evaluators (autoevals adapters)

Built on top of the [autoevals](https://github.com/braintrustdata/autoevals) package. Each wraps an autoevals `Scorer` and returns a pixie `Evaluator` callable.

```python
from pixie.evals import (
    AutoevalsAdapter,
    LevenshteinMatch, ExactMatchEval, NumericDiffEval,
    JSONDiffEval, ValidJSONEval, ListContainsEval,
    EmbeddingSimilarityEval,
    FactualityEval, ClosedQAEval, BattleEval,
    HumorEval, SecurityEval, SqlEval,
    SummaryEval, TranslationEval, PossibleEval,
    ModerationEval,
    ContextRelevancyEval, FaithfulnessEval,
    AnswerRelevancyEval, AnswerCorrectnessEval,
)
```

**Heuristic (no LLM required):**

- `LevenshteinMatch(expected=...)` — edit-distance string similarity
- `ExactMatchEval(expected=...)` — exact value comparison
- `NumericDiffEval(expected=...)` — normalised numeric difference
- `JSONDiffEval(expected=...)` — structural JSON comparison
- `ValidJSONEval(schema=...)` — JSON syntax / schema validation
- `ListContainsEval(expected=...)` — list overlap

**LLM-as-judge (require OpenAI or proxy):**

- `FactualityEval(expected=..., model=..., client=...)` — factual accuracy
- `ClosedQAEval(expected=..., model=..., client=...)` — closed-book QA
- `BattleEval(expected=..., model=..., client=...)` — head-to-head comparison
- `HumorEval(model=..., client=...)` — humor detection
- `SecurityEval(model=..., client=...)` — security vulnerability check
- `SqlEval(expected=..., model=..., client=...)` — SQL equivalence
- `SummaryEval(expected=..., model=..., client=...)` — summarisation quality
- `TranslationEval(expected=..., language=..., model=..., client=...)` — translation quality
- `PossibleEval(model=..., client=...)` — feasibility check

**Other:**

- `EmbeddingSimilarityEval(expected=..., prefix=..., model=..., client=...)` — embedding similarity
- `ModerationEval(threshold=..., client=...)` — content moderation
- `ContextRelevancyEval(expected=..., client=...)` — RAGAS context relevancy
- `FaithfulnessEval(client=...)` — RAGAS faithfulness
- `AnswerRelevancyEval(client=...)` — RAGAS answer relevancy
- `AnswerCorrectnessEval(expected=..., client=...)` — RAGAS answer correctness

**Generic adapter for any autoevals scorer:**

- `AutoevalsAdapter(scorer, *, expected=..., input_key=..., extra_metadata_keys=(...,))` — wraps any autoevals `Scorer`

**Example:**

```python
from pixie.evals import evaluate, LevenshteinMatch, FactualityEval

# Heuristic — no LLM needed
evaluator = LevenshteinMatch(expected="hello world")
result = await evaluate(evaluator, evaluable)
print(result.score)  # e.g. 0.91

# LLM-as-judge
evaluator = FactualityEval(expected="Paris is the capital of France")
result = await evaluate(evaluator, evaluable)
print(result.reasoning)  # CoT rationale from the LLM judge
```

### Configuration

All settings are read from `PIXIE_`-prefixed environment variables at call time:

| Variable            | Default                 | Description                         |
| ------------------- | ----------------------- | ----------------------------------- |
| `PIXIE_DB_PATH`     | `pixie_observations.db` | SQLite database file path           |
| `PIXIE_DB_ENGINE`   | `sqlite`                | Database engine type                |
| `PIXIE_DATASET_DIR` | `pixie_datasets`        | Directory for dataset JSON files    |

```python
from pixie.config import get_config
config = get_config()  # reads env vars with defaults
```

**Example evaluator:**

```python
async def exact_match(evaluable: Evaluable, *, trace=None) -> Evaluation:
    match = str(evaluable.eval_output).strip().lower() == "expected"
    return Evaluation(
        score=1.0 if match else 0.0,
        reasoning="Exact match" if match else "No match",
    )
```

**Example test:**

```python
import asyncio
from pixie.evals import assert_pass, Evaluation, ScoreThreshold, last_llm_call
from pixie.storage.evaluable import Evaluable

def my_app(question):
    import pixie.instrumentation as px
    with px.log(input=question, name="qa") as span:
        span.set_output("expected")

async def test_my_app():
    await assert_pass(
        runnable=my_app,
        inputs=["What is 2+2?"],
        evaluators=[exact_match],
    )

# With expected outputs via evaluables
async def test_with_expected():
    items = [
        Evaluable(eval_input="What is 2+2?", expected_output="4"),
        Evaluable(eval_input="Capital of France?", expected_output="Paris"),
    ]
    await assert_pass(
        runnable=my_app,
        inputs=[item.eval_input for item in items],
        evaluators=[FactualityEval()],
        evaluables=items,
    )

# With custom pass criteria
async def test_with_threshold():
    await assert_pass(
        runnable=my_app,
        inputs=["q1", "q2", "q3"],
        evaluators=[exact_match],
        pass_criteria=ScoreThreshold(threshold=0.7, pct=0.8),
        passes=3,
    )

# Evaluate last LLM call instead of root span
async def test_llm_output():
    await assert_pass(
        runnable=my_app,
        inputs=["What is 2+2?"],
        evaluators=[exact_match],
        from_trace=last_llm_call,
    )
```

### Dataset Management

```python
from pixie.dataset import Dataset, DatasetStore
from pixie.storage.evaluable import Evaluable

store = DatasetStore()

# Create a dataset with test cases
ds = store.create("qa-golden-set", items=[
    Evaluable(eval_input="What is 2+2?", expected_output="4"),
    Evaluable(eval_input="Capital of France?", expected_output="Paris"),
])

# Append more items
store.append("qa-golden-set", Evaluable(eval_input="Hello", expected_output="Hi"))

# Load and use with eval harness
ds = store.get("qa-golden-set")
await assert_pass(
    runnable=my_qa_app,
    inputs=[item.eval_input for item in ds.items],
    evaluators=[FactualityEval()],
    evaluables=list(ds.items),
)

# List all datasets
names = store.list()  # ["qa-golden-set"]

# Remove an item by index
store.remove("qa-golden-set", index=2)

# Delete a dataset
store.delete("qa-golden-set")
```

### CLI

```bash
pixie-test [path] [-k filter] [-v]
```

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
uv run pytest tests/pixie/evals -v
uv run pytest tests/pixie/dataset -v
```

## Documentation

- Instrumentation spec: `specs/instrumentation.md`
- Storage spec: `specs/storage.md`
- Evals harness spec: `specs/evals-harness.md`
- Autoevals adapters spec: `specs/autoevals-adapters.md`
- Usability improvements spec: `specs/usability-utils.md`
- Dataset management spec: `specs/dataset-management.md`
- Change history: `changelogs/`

## Dev Setup (Skills)

```bash
npx openskills install anthropics/skills
```
