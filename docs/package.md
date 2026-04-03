# pixie-qa Python Package

`pixie-qa` (imported as `pixie`) is the Python library that powers eval-driven development for LLM applications. It handles tracing, dataset management, and evaluation harness so you can write tests that measure quality.

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

| Variable                   | Default                    | Description                                 |
| -------------------------- | -------------------------- | ------------------------------------------- |
| `PIXIE_ROOT`               | `pixie_qa`                 | Root directory for all Pixie artefacts      |
| `PIXIE_DB_PATH`            | `pixie_qa/observations.db` | SQLite database file path                   |
| `PIXIE_DB_ENGINE`          | `sqlite`                   | Database engine type                        |
| `PIXIE_DATASET_DIR`        | `pixie_qa/datasets`        | Directory for dataset JSON files            |
| `PIXIE_RATE_LIMIT_ENABLED` | disabled                   | Enables evaluator rate limiting when `true` |
| `PIXIE_RATE_LIMIT_RPS`     | `4.0`                      | Max evaluator requests per second           |
| `PIXIE_RATE_LIMIT_RPM`     | `50.0`                     | Max evaluator requests per minute           |
| `PIXIE_RATE_LIMIT_TPS`     | `10000.0`                  | Max evaluator tokens per second             |
| `PIXIE_RATE_LIMIT_TPM`     | `500000.0`                 | Max evaluator tokens per minute             |

When rate limiting is enabled, unset `PIXIE_RATE_LIMIT_*` values fall back to the defaults above.

---

## Local Storage Tracking

Call `enable_storage()` once at application startup. It creates the SQLite database, registers the storage handler, and initialises the OTel pipeline — all in one line:

```python
from pixie import enable_storage

enable_storage()
```

This is idempotent: safe to call multiple times.

After calling `enable_storage()`, wrap the function(s) you want to evaluate with `@observe` or `start_observation`. Every call will be persisted automatically:

```python
from pixie import enable_storage, observe, start_observation, flush

enable_storage()

# Decorator style — captures all kwargs as eval_input, return value as eval_output
@observe(name="answer_question")
def answer_question(question: str) -> str:
    ...

# Context-manager style — for more control over what gets captured
with start_observation(input={"question": question}, name="answer_question") as obs:
    result = run_pipeline(question)
    obs.set_output(result)
    obs.set_metadata("retrieved_chunks", 3)

# Flush at the end of a script/run so all spans are written before you use CLI commands
flush()
```

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

## Dataset Management (CLI)

`pixie` includes a CLI for building and managing golden datasets from captured traces.

```bash
# Create a new empty dataset
pixie dataset create <name>

# List all datasets
pixie dataset list

# Save the last captured trace to a dataset
pixie dataset save <name>                                      # root span (default)
pixie dataset save <name> --select last_llm_call               # last LLM call in the trace
pixie dataset save <name> --select by_name --span-name <name>  # span matching a name
pixie dataset save <name> --notes "some context note"          # attach metadata

# Pipe in an expected output when saving
echo '"Paris"' | pixie dataset save <name> --expected-output
```

**Selection modes** for `pixie dataset save`:

| Mode             | What is saved                                       |
| ---------------- | --------------------------------------------------- |
| `root` (default) | The outermost `@observe` / `start_observation` span |
| `last_llm_call`  | The most recent LLM API call span in the trace      |
| `by_name`        | The last span matching the `--span-name` argument   |

Dataset files are stored as JSON under `PIXIE_DATASET_DIR` (default: `pixie_qa/datasets/`). Each item is an `Evaluable` with `eval_input`, `eval_output`, optional `expected_output`, and `eval_metadata`.

---

## DAG Validation And Trace Alignment

Use DAG files to describe your app's processing graph and validate trace coverage:

```bash
pixie dag validate pixie_qa/02-data-flow.json --project-root .
pixie dag check-trace pixie_qa/02-data-flow.json
```

Current DAG node schema:

- Required: `name`, `code_pointer`, `description`
- Optional: `parent`, `is_llm_call`, `metadata`
- `name` is the unique lower_snake_case identifier (for example, `handle_turn`)
- `is_llm_call` defaults to `false` when omitted

`check-trace` semantics:

- `is_llm_call: true` nodes pass if at least one LLM span exists (name matching skipped)
- non-LLM nodes (`is_llm_call` false/omitted) require exact span-name match to a non-LLM span
- if a node is marked non-LLM but only an LLM span matches the name, the check reports a flag mismatch

---

## Writing Eval-Based Tests

Use `assert_dataset_pass` (or `assert_pass` for inline inputs) to write quality tests. Tests live in regular `test_*.py` files and are run with `pixie-test`.

### Minimal test

```python
from pixie import enable_storage, assert_dataset_pass, FactualityEval, ScoreThreshold

from myapp import answer_question


def runnable(eval_input):
    """Runs one dataset item through the app. enable_storage() here ensures each run is traced."""
    enable_storage()
    answer_question(**eval_input)  # or answer_question(eval_input) if input is a plain string


async def test_factuality():
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name="qa-golden-set",
        evaluators=[FactualityEval()],
        pass_criteria=ScoreThreshold(threshold=0.7, pct=0.8),
    )
```

If your runnable is synchronous but internally drives async code (for example via
`asyncio.get_event_loop().run_until_complete(...)`), pixie provisions a
thread-local event loop when executing sync runnables so this compatibility
pattern works under `pixie test`.

> `enable_storage()` belongs inside `runnable`, not at module level — it needs to fire on every invocation so the trace is captured for that specific run.

### Evaluating the last LLM call instead of the root span

```python
from pixie import assert_dataset_pass, FactualityEval, last_llm_call

async def test_llm_output():
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name="qa-golden-set",
        evaluators=[FactualityEval()],
        from_trace=last_llm_call,   # evaluate the LLM span, not the root observe span
    )
```

### Inline inputs (no dataset file)

```python
from pixie import assert_pass, LevenshteinMatch

async def test_inline():
    await assert_pass(
        runnable=runnable,
        eval_inputs=["What is 2+2?", "Capital of France?"],
        evaluators=[LevenshteinMatch(expected="4")],
    )
```

### Built-in evaluators (quick reference)

**Heuristic (no LLM required):**

| Evaluator                        | What it measures                |
| -------------------------------- | ------------------------------- |
| `LevenshteinMatch(expected=...)` | Edit-distance string similarity |
| `ExactMatchEval(expected=...)`   | Exact value comparison          |
| `ValidJSONEval(schema=...)`      | JSON syntax / schema validation |
| `JSONDiffEval(expected=...)`     | Structural JSON similarity      |
| `NumericDiffEval(expected=...)`  | Normalised numeric difference   |
| `ListContainsEval(expected=...)` | List overlap                    |

**LLM-as-judge (require an OpenAI-compatible endpoint):**

| Evaluator                             | What it measures                     |
| ------------------------------------- | ------------------------------------ |
| `FactualityEval(expected=...)`        | Factual accuracy against a reference |
| `ClosedQAEval(expected=...)`          | Closed-book question answering       |
| `SummaryEval(expected=...)`           | Summarisation quality                |
| `ContextRelevancyEval(expected=...)`  | RAG context relevancy                |
| `FaithfulnessEval()`                  | RAG faithfulness                     |
| `AnswerRelevancyEval()`               | RAG answer relevancy                 |
| `AnswerCorrectnessEval(expected=...)` | RAG answer correctness               |

All evaluators are importable from `pixie` (e.g. `from pixie import FactualityEval`). See the [full API docs](#full-api-documentation) for the complete list and signatures.

---

## Running Tests

Use `pixie test` (or the equivalent `pixie-test` entry point, not bare `pytest`)
to run eval tests. It sets up the async environment and provides eval-specific
output formatting:

```bash
pixie test                 # run all test_*.py in the current directory
pixie test tests/          # specify a path
pixie test -k factuality   # filter by name substring
pixie test -v              # verbose: shows per-case scores and reasoning
```

`pixie test` applies the central Pixie config before running evaluators, so `.env`-backed `PIXIE_RATE_LIMIT_*` settings are honored automatically.

### Test Results (JSON)

Every `pixie test` run generates a **JSON result file** saved to `{PIXIE_ROOT}/results/<test_id>/result.json`, where `<test_id>` is a timestamp like `20250615-120000`. After generating the result, `pixie test` opens the web UI (see [Web UI](#web-ui)) with the Results tab selected. If the web UI server is not already running, one is started in the background automatically.

Pass `--no-open` to suppress automatic browser opening.

The JSON result contains:

- **Meta** — test ID, command args, start/end timestamps.
- **Datasets** — array of per-dataset results, each containing:
  - Dataset name and optional analysis (markdown).
  - Per-entry results with input, output, expected output, description, and evaluations.
  - Each evaluation has evaluator name, score, and reasoning.

After the test run, the CLI prints the result path:

```text
Result saved to /path/to/pixie_qa/results/20250615-120000/result.json
```

### Analysing Test Results

Use `pixie analyze` to generate LLM-powered analysis for each dataset in a test run:

```bash
pixie analyze <test_id>    # e.g. pixie analyze 20250615-120000
```

This calls an OpenAI-compatible model (configurable via `PIXIE_ANALYZE_MODEL`, default: `gpt-4o-mini`) to produce a markdown analysis for each dataset. Analysis files are saved alongside the result as `dataset-<index>.md` and are merged into the result when loaded by the web UI.

### Legacy HTML Scorecards

Older `pixie test` runs that produced standalone HTML scorecards are still viewable in the Scorecards tab of the web UI.

---

## Web UI

View all generated artifacts — results, markdown documents, datasets, and legacy scorecards — in a live-updating local web UI:

```bash
pixie start              # starts server on port 7118 and opens browser
pixie start my_dir       # use a custom artifact root directory
```

The web UI provides:

- **Tabbed navigation** — Results tab, Scorecards tab, Datasets tab, plus one tab per markdown file
- **Results panel** — sidebar list of test runs with a result viewer showing test overview, per-dataset analysis, and per-entry evaluation details
- **Scorecards panel** — sidebar list of legacy HTML scorecards with iframe viewer
- **Datasets panel** — sidebar list of datasets with table viewer
- **Markdown panel** — renders `.md` files as formatted HTML
- **Live updates** — file changes are pushed to the browser via SSE; the view automatically switches to the updated artifact

If the default port (7118) is already in use, `pixie start` assumes the server is running and opens the browser only.

The web UI server is built with Starlette + Uvicorn and watches the artifact root with `watchfiles` for real-time change detection.

---

## Full API Documentation

The features above cover the typical day-to-day workflow. For complete reference — including custom handlers, custom evaluators, the `ObservationStore` query API, programmatic dataset management, and all configuration options — see the generated pydoc:

```bash
python -m pydoc pixie
python -m pydoc pixie.evals
python -m pydoc pixie.instrumentation
python -m pydoc pixie.storage
python -m pydoc pixie.dataset
```

Or browse the source-level specs in [`specs/`](../specs/).
