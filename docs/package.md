# pixie-qa Python Package

`pixie-qa` (imported as `pixie`) is the Python library that powers eval-driven development for LLM applications. It handles instrumentation, dataset management, and evaluation so you can write tests that measure quality.

## Installation

```bash
pip install pixie-qa
# or, if you use uv:
uv add pixie-qa
```

Provider instrumentation extras (auto-trace LLM API calls):

```bash
pip install "pixie-qa[openai]"       # OpenAI
pip install "pixie-qa[anthropic]"    # Anthropic
pip install "pixie-qa[langchain]"    # LangChain
pip install "pixie-qa[google]"       # Google Generative AI
pip install "pixie-qa[dspy]"         # DSPy
pip install "pixie-qa[all]"          # all of the above
```

## Configuration

Settings are read from process environment variables and a local `.env` file at call time. Existing process env vars take precedence over `.env` values.

| Variable                   | Default              | Description                                         |
| -------------------------- | -------------------- | --------------------------------------------------- |
| `PIXIE_ROOT`               | `pixie_qa`           | Root directory for all Pixie artefacts              |
| `PIXIE_DATASET_DIR`        | `{PIXIE_ROOT}/datasets` | Directory for dataset JSON files                 |
| `PIXIE_RATE_LIMIT_ENABLED` | disabled             | Enables evaluator rate limiting when `true`         |
| `PIXIE_RATE_LIMIT_RPS`     | `4.0`                | Max evaluator requests per second                   |
| `PIXIE_RATE_LIMIT_RPM`     | `50.0`               | Max evaluator requests per minute                   |
| `PIXIE_RATE_LIMIT_TPS`     | `10000.0`            | Max evaluator tokens per second                     |
| `PIXIE_RATE_LIMIT_TPM`     | `500000.0`           | Max evaluator tokens per minute                     |
| `PIXIE_TRACE_OUTPUT`       | (none)               | Path for JSONL trace output file                    |
| `PIXIE_TRACING`            | disabled             | Enables tracing mode when `1`/`true`/`yes`/`on`     |
| `PIXIE_ANALYZE_MODEL`      | `gpt-4o-mini`        | OpenAI model used by `pixie analyze`                |

When rate limiting is enabled, unset `PIXIE_RATE_LIMIT_*` values fall back to the defaults above.

---

## LLM Tracing

Call `enable_llm_tracing()` to initialize the OpenTelemetry tracing pipeline and auto-discover instrumentors for supported LLM providers (OpenAI, Anthropic, LangChain, Google GenAI, DSPy):

```python
from pixie import enable_llm_tracing, add_handler, flush

enable_llm_tracing()
```

This is idempotent: safe to call multiple times.

After enabling tracing, register one or more `InstrumentationHandler` subclasses to receive typed span notifications:

```python
from pixie.instrumentation import InstrumentationHandler, LLMSpan

class MyHandler(InstrumentationHandler):
    async def on_llm(self, span: LLMSpan) -> None:
        print(f"LLM call: {span.request_model} ({span.input_tokens} in, {span.output_tokens} out)")

add_handler(MyHandler())

# ... run your application ...

# Flush pending spans at the end of a script/run
flush()
```

### The `wrap()` API

Use `wrap()` for data-oriented observation — dependency injection during evaluation and output capture during tracing:

```python
from pixie import wrap

# Mark a value as an input dependency (injected from dataset during pixie test)
db_result = wrap(fetch_from_db(query), purpose="input", name="db_result")

# Mark a callable — its return value is captured as output
summarize = wrap(my_summarize_fn, purpose="output", name="summary")
result = summarize(text)

# Mark internal state for observability
wrap(intermediate_data, purpose="state", name="retrieval_context")
```

**Purposes:**

| Purpose    | Behavior during `pixie test`                  | Behavior during `pixie trace`        |
| ---------- | --------------------------------------------- | ------------------------------------ |
| `"input"`  | Injects value from dataset (replaces computation) | Emits observation to trace file  |
| `"output"` | Captures value for evaluation                 | Emits observation to trace file      |
| `"state"`  | Captures value for evaluation                 | Emits observation to trace file      |

---

## Project Scaffolding (CLI)

Scaffold the standard `pixie_qa/` working directory for eval-driven development:

```bash
pixie init              # creates pixie_qa/ with datasets/, tests/, scripts/
pixie init my_dir       # use a custom root directory
```

The command is idempotent — existing files and directories are never overwritten or deleted. Respects the `PIXIE_ROOT` environment variable when no argument is provided.

`pixie start` also runs init automatically before starting the server, so a separate `pixie init` is only needed when you want to scaffold without starting the web UI.

---

## Dataset JSON Format

Datasets are JSON files that define test scenarios for `pixie test`. Each dataset specifies a runnable, default evaluators, and a list of entries.

### Top-Level Fields

| Field          | Type       | Required | Description                                                  |
| -------------- | ---------- | -------- | ------------------------------------------------------------ |
| `name`         | `string`   | No       | Display name (defaults to filename stem)                     |
| `runnable`     | `string`   | Yes      | `filepath:callable_name` reference to the function or Runnable class |
| `evaluators`   | `string[]` | No       | Default evaluator names applied to entries without row-level overrides |
| `entries`      | `object[]` | Yes      | Array of dataset entries (see below)                         |

### Entry Fields

| Field             | Type       | Required | Description                                          |
| ----------------- | ---------- | -------- | ---------------------------------------------------- |
| `entry_kwargs`    | `object`   | Yes      | Arguments passed to the runnable                     |
| `test_case`       | `object`   | Yes      | Scenario definition (see below)                      |
| `evaluators`      | `string[]` | No       | Row-level evaluators; `"..."` includes dataset defaults |

### TestCase Fields

| Field            | Type       | Required | Description                                       |
| ---------------- | ---------- | -------- | ------------------------------------------------- |
| `description`    | `string`   | Yes      | Human-readable label for this test case           |
| `eval_input`     | `array`    | Yes      | List of `{"name": ..., "value": ...}` items       |
| `expectation`    | `any`      | No       | Reference value for comparison-based evaluators   |
| `eval_metadata`  | `object`   | No       | Supplementary metadata (e.g. `context` for RAG)   |

### Evaluator Name Resolution

- **Built-in names** (e.g. `"Factuality"`, `"ExactMatch"`) are resolved to `pixie.{Name}` automatically.
- **Custom evaluators** use `filepath:callable_name` format (e.g. `"pixie_qa/evaluators.py:ConciseVoiceStyle"`).
- Custom evaluator references can point to:
  - **Classes** — instantiated via `cls()`.
  - **Zero-arg factory functions** (like built-in `ExactMatch`) — called to produce the evaluator.
  - **Evaluator functions** with required parameters — used as-is.
  - **Pre-instantiated callables** (e.g. `create_llm_evaluator()` results) — used as-is.

### Validation Rules

- `runnable` is required and must resolve to a valid callable.
- Every entry must include a non-empty `test_case.description`.
- Every entry must resolve to at least one evaluator (from row-level evaluators, dataset defaults, or both).
- All evaluator names must resolve to valid evaluator callables.

### Example Dataset

```json
{
  "name": "qa-tests",
  "runnable": "pixie_qa/scripts/run_app.py:run_app",
  "evaluators": ["Factuality", "ClosedQA"],
  "entries": [
    {
      "entry_kwargs": {"question": "What is 2+2?"},
      "test_case": {
        "description": "Simple arithmetic",
        "eval_input": [{"name": "question", "value": "What is 2+2?"}],
        "expectation": "4"
      }
    },
    {
      "entry_kwargs": {"question": "Capital of France?"},
      "test_case": {
        "description": "Geography question",
        "eval_input": [{"name": "question", "value": "Capital of France?"}],
        "expectation": "Paris"
      },
      "evaluators": ["...", "ExactMatch"]
    }
  ]
}
```

---

## Runnables

A **runnable** is the function (or class) that `pixie test` calls for each dataset entry. It produces evaluation output from input arguments.

### Plain Callable

Any sync or async function that accepts a `dict` of kwargs:

```python
# pixie_qa/scripts/run_app.py
def run_app(kwargs: dict) -> str:
    question = kwargs["question"]
    return my_pipeline(question)
```

Referenced in the dataset as `"pixie_qa/scripts/run_app.py:run_app"`.

### Runnable Protocol

For runnables that need setup/teardown lifecycle hooks, implement the `Runnable` protocol with a Pydantic model for typed arguments:

```python
from pydantic import BaseModel
from pixie.harness.runnable import Runnable

class AppArgs(BaseModel):
    question: str

class MyRunnable:
    @classmethod
    def create(cls) -> "MyRunnable":
        return cls()

    async def setup(self) -> None:
        # Called once before all entries
        pass

    async def teardown(self) -> None:
        # Called once after all entries
        pass

    async def run(self, args: AppArgs) -> None:
        # Called for each dataset entry
        result = my_pipeline(args.question)
        wrap(result, purpose="output", name="answer")
```

The runner calls `create()` → `setup()` → `run(args)` for each entry → `teardown()`.

---

## Custom Evaluators

### Using `create_llm_evaluator`

Build custom LLM-as-judge evaluators from prompt templates:

```python
from pixie import create_llm_evaluator

concise_voice_style = create_llm_evaluator(
    name="ConciseVoiceStyle",
    prompt_template="""
    You are evaluating whether a voice agent response is concise and
    phone-friendly.

    User said: {eval_input}
    Agent responded: {eval_output}
    Expected behavior: {expectation}

    Score 1.0 if the response is concise (under 3 sentences), directly
    addresses the question, and uses conversational language suitable for
    a phone call. Score 0.0 if it's verbose, off-topic, or uses
    written-style formatting.
    """,
)
```

Template placeholders (`{eval_input}`, `{eval_output}`, `{expectation}`) are populated from the `Evaluable` fields. Dict values are automatically serialized to JSON.

Reference the evaluator in a dataset file using `filepath:callable_name` format.

### Writing an Evaluator Function

Any async or sync callable that accepts an `Evaluable` and returns an `Evaluation`:

```python
from pixie.eval.evaluable import Evaluable
from pixie.eval.evaluation import Evaluation

async def my_evaluator(evaluable: Evaluable) -> Evaluation:
    output = evaluable.eval_output[0].value
    expected = evaluable.expectation
    score = 1.0 if output == expected else 0.0
    return Evaluation(score=score, reasoning="Exact match check")
```

---

## Built-in Evaluators

All built-in evaluators are importable from `pixie` (e.g. `from pixie import Factuality`).

### Heuristic (no LLM required)

| Evaluator           | What it measures                | Requires `expectation` |
| ------------------- | ------------------------------- | ---------------------- |
| `LevenshteinMatch`  | Edit-distance string similarity | Yes                    |
| `ExactMatch`        | Exact value comparison          | Yes                    |
| `NumericDiff`       | Normalised numeric difference   | Yes                    |
| `JSONDiff`          | Structural JSON comparison      | Yes                    |
| `ValidJSON`         | JSON syntax / schema validation | No                     |
| `ListContains`      | List overlap                    | Yes                    |

### Embedding

| Evaluator              | What it measures                | Requires `expectation` |
| ---------------------- | ------------------------------- | ---------------------- |
| `EmbeddingSimilarity`  | Cosine similarity via embeddings | Yes                   |

### LLM-as-judge (require an OpenAI-compatible endpoint)

| Evaluator     | What it measures                     | Requires `expectation` |
| ------------- | ------------------------------------ | ---------------------- |
| `Factuality`  | Factual accuracy against a reference | Yes                    |
| `ClosedQA`    | Closed-book question answering       | Yes                    |
| `Battle`      | Head-to-head comparison              | Yes                    |
| `Humor`       | Humor quality                        | Yes                    |
| `Security`    | Security vulnerability check         | No                     |
| `Sql`         | SQL equivalence                      | Yes                    |
| `Summary`     | Summarisation quality                | Yes                    |
| `Translation` | Translation quality                  | Yes                    |
| `Possible`    | Feasibility / plausibility           | No                     |

### Moderation

| Evaluator    | What it measures             | Requires `expectation` |
| ------------ | ---------------------------- | ---------------------- |
| `Moderation` | Content safety (OpenAI API)  | No                     |

### RAGAS Metrics

| Evaluator           | What it measures        | Requires `expectation` | Requires `eval_metadata["context"]` |
| ------------------- | ----------------------- | ---------------------- | ----------------------------------- |
| `ContextRelevancy`  | Retrieval quality       | Yes                    | Yes                                 |
| `Faithfulness`      | Answer grounding        | No                     | Yes                                 |
| `AnswerRelevancy`   | Answer relevance        | No                     | Yes                                 |
| `AnswerCorrectness` | Comprehensive correctness | Yes                  | Optional                            |

**Critical rules:**

- For open-ended LLM text, **never** use `ExactMatch` — LLM outputs are non-deterministic.
- `AnswerRelevancy` is **RAG-only** — requires `context` in `eval_metadata`. Returns 0.0 without it.
- Do NOT use comparison evaluators (`Factuality`, `ClosedQA`, `ExactMatch`) on items without `expectation`.

---

## Running Tests

Use `pixie test` to run dataset-driven evaluations:

```bash
pixie test                              # all datasets in PIXIE_DATASET_DIR
pixie test path/to/dataset.json         # single dataset file
pixie test path/to/datasets/            # all datasets in a directory
pixie test -v                           # verbose: show reasoning for failures
pixie test --no-open                    # suppress automatic browser opening
```

`pixie test` applies the central Pixie config before running evaluators, so `.env`-backed `PIXIE_RATE_LIMIT_*` settings are honored automatically.

### Test Results (JSON)

Every `pixie test` run generates a **JSON result file** saved to `{PIXIE_ROOT}/results/<test_id>/result.json`, where `<test_id>` is a timestamp like `20260403-120000`. After generating the result, `pixie test` opens the web UI (see [Web UI](#web-ui)) with the Results tab selected. If the web UI server is not already running, one is started in the background automatically.

Pass `--no-open` to suppress automatic browser opening.

The JSON result contains:

- **Meta** — test ID, command args, start/end timestamps.
- **Datasets** — array of per-dataset results, each containing:
  - Dataset name and optional analysis (markdown).
  - Per-entry results with input, output, expected output, description, and evaluations.
  - Each evaluation has evaluator name, score, and reasoning.

After the test run, the CLI prints the result path:

```text
Results saved to /path/to/pixie_qa/results/20260403-120000/result.json
```

### Analysing Test Results

Use `pixie analyze` to generate LLM-powered analysis for each dataset in a test run:

```bash
pixie analyze <test_id>    # e.g. pixie analyze 20260403-120000
```

This calls an OpenAI-compatible model (configurable via `PIXIE_ANALYZE_MODEL`, default: `gpt-4o-mini`) to produce a markdown analysis for each dataset. Analysis files are saved alongside the result as `dataset-<index>.md` and are merged into the result when loaded by the web UI.

---

## Tracing and Dataset Building

Use `pixie trace` and `pixie format` to record application runs and convert them into dataset entries.

### Recording a Trace

```bash
pixie trace --runnable path/to/app.py:MyRunnable \
            --input kwargs.json \
            --output trace.jsonl
```

This runs the specified runnable with the kwargs from the input JSON file, capturing all `wrap()` events and LLM spans to a JSONL trace file.

### Converting a Trace to a Dataset Entry

```bash
pixie format --input trace.jsonl --output entry.json
```

Parses the trace file and extracts:
- `wrap(purpose="input")` events → `eval_input`
- `wrap(purpose="output"/"state")` events and LLM spans → `expectation`

The resulting JSON can be added to a dataset file's `entries` array.

---

## Web UI

View all generated artifacts — results, markdown documents, datasets, and scorecards — in a live-updating local web UI:

```bash
pixie start              # starts server on port 7118 and opens browser
pixie start my_dir       # use a custom artifact root directory
```

The web UI provides:

- **Tabbed navigation** — Results, Scorecards, Datasets, plus one tab per markdown file.
- **Results panel** — sidebar list of test runs with a result viewer showing test overview, per-dataset analysis, and per-entry evaluation details.
- **Scorecards panel** — sidebar list of HTML scorecards with iframe viewer.
- **Datasets panel** — sidebar list of datasets with table viewer.
- **Markdown panel** — renders `.md` files as formatted HTML.
- **Live updates** — file changes are pushed to the browser via SSE; the view automatically refreshes.

If the default port (7118) is already in use, `pixie start` detects the running server and opens the browser to the existing instance.

The web UI server is built with Starlette + Uvicorn and watches the artifact root with `watchfiles` for real-time change detection. A `server.lock` file in the artifact root records the port for inter-process discovery.

---

## CLI Reference

| Command                                                                 | Description                                     |
| ----------------------------------------------------------------------- | ----------------------------------------------- |
| `pixie test [path] [-v] [--no-open]`                                    | Run dataset-driven eval tests                   |
| `pixie analyze <test_run_id>`                                           | Generate LLM analysis of a test run             |
| `pixie init [root]`                                                     | Scaffold the pixie_qa working directory         |
| `pixie start [root]`                                                    | Launch the web UI                               |
| `pixie trace --runnable <ref> --input <file> --output <file>`           | Record a runnable execution as a JSONL trace    |
| `pixie format --input <file> --output <file>`                           | Convert a trace log to a dataset entry          |

---

## Full API Documentation

For complete reference — including custom handlers, custom evaluators, and all configuration options — see the module docstrings:

```bash
python -m pydoc pixie
python -m pydoc pixie.eval
python -m pydoc pixie.instrumentation
python -m pydoc pixie.harness
python -m pydoc pixie.web
```

Or browse the source-level specs in [`specs/`](../specs/).
