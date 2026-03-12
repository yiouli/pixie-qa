# pixie Python Package

`pixie` is the Python library that powers eval-driven development for LLM applications. It handles tracing, dataset management, and evaluation harness so you can write tests that measure quality.

## Installation

```bash
pip install pixie
# or, if you use uv:
uv add pixie
```

Provider instrumentation extras (auto-trace LLM API calls):

```bash
pip install "pixie[openai]"       # OpenAI
pip install "pixie[anthropic]"    # Anthropic
pip install "pixie[langchain]"    # LangChain
pip install "pixie[google]"       # Google Generative AI
pip install "pixie[dspy]"         # DSPy
pip install "pixie[all]"          # all of the above
```

## Configuration

Settings are read from environment variables at call time:

| Variable            | Default                 | Description                      |
| ------------------- | ----------------------- | -------------------------------- |
| `PIXIE_DB_PATH`     | `pixie_observations.db` | SQLite database file path        |
| `PIXIE_DATASET_DIR` | `pixie_datasets`        | Directory for dataset JSON files |

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
import pixie.instrumentation as px

# Decorator style — captures all kwargs as eval_input, return value as eval_output
@px.observe(name="answer_question")
def answer_question(question: str) -> str:
    ...

# Context-manager style — for more control over what gets captured
with px.start_observation(input={"question": question}, name="answer_question") as obs:
    result = run_pipeline(question)
    obs.set_output(result)
    obs.set_metadata("retrieved_chunks", 3)

# Flush at the end of a script/run so all spans are written before you use CLI commands
px.flush()
```

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

Dataset files are stored as JSON under `PIXIE_DATASET_DIR` (default: `pixie_datasets/`). Each item is an `Evaluable` with `eval_input`, `eval_output`, optional `expected_output`, and `eval_metadata`.

---

## Writing Eval-Based Tests

Use `assert_dataset_pass` (or `assert_pass` for inline inputs) to write quality tests. Tests live in regular `test_*.py` files and are run with `pixie-test`.

### Minimal test

```python
from pixie import enable_storage
from pixie.evals import assert_dataset_pass, FactualityEval, ScoreThreshold

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

> `enable_storage()` belongs inside `runnable`, not at module level — it needs to fire on every invocation so the trace is captured for that specific run.

### Evaluating the last LLM call instead of the root span

```python
from pixie.evals import assert_dataset_pass, FactualityEval, last_llm_call

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
from pixie.evals import assert_pass, LevenshteinMatch

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

All evaluators are importable from `pixie.evals`. See the [full API docs](#full-api-documentation) for the complete list and signatures.

---

## Running Tests

Use `pixie-test` (not bare `pytest`) to run eval tests. It sets up the async environment and provides eval-specific output formatting:

```bash
pixie-test                 # run all test_*.py in the current directory
pixie-test tests/          # specify a path
pixie-test -k factuality   # filter by name substring
pixie-test -v              # verbose: shows per-case scores and reasoning
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
