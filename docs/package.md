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
pixie init              # creates pixie_qa/ with datasets/, tests/, scripts/, MEMORY.md
pixie init my_dir       # use a custom root directory
```

The command is idempotent — existing files and directories are never overwritten or deleted. Respects the `PIXIE_ROOT` environment variable when no argument is provided.

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

### HTML Scorecard

Every `pixie test` run generates an **HTML scorecard** saved to `{PIXIE_ROOT}/scorecards/<timestamp>.html`. The scorecard is a self-contained React application compiled to a single HTML file — no external dependencies, works from `file://`.

The scorecard contains:

- **Test run overview** — command args, timestamp, pass/fail summary, and a table of all tests with their status.
- **Per-test detail** — for each test function that calls `assert_pass` / `assert_dataset_pass`:
  - Scoring strategy description (human-readable).
  - Per-evaluator pass rate table.
  - Per-input × per-evaluator score grid with detail links.
  - **Tabbed view** for multi-pass runs (one tab per pass).
- **Evaluation detail modal** — click any score to see full reasoning, input, expected/actual output, and metadata.
- **Feedback modal** — share feedback directly from the scorecard.

The frontend source lives in `frontend/` and compiles to `pixie/assets/index.html` via Vite. At runtime, Python injects JSON data into the template. See [frontend/README.md](../frontend/README.md) for development and build instructions.

After the test run, the CLI prints the scorecard path:

```text
See /path/to/pixie_qa/scorecards/20250615-120000-pixie-test.html for test details
```

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
