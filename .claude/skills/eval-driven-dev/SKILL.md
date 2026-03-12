---
name: eval-driven-dev
description: Instrument Python LLM apps, build golden datasets, write eval-based tests, run them, and root-cause failures — covering the full eval-driven development cycle. Make sure to use this skill whenever a user is developing, testing, QA-ing, evaluating, or benchmarking a Python project that calls an LLM, even if they don't say "evals" explicitly. Use for making sure an AI app works correctly, catching regressions after prompt changes, debugging why an agent started behaving differently, or validating output quality before shipping.
---

# Eval-Driven Development with pixie

This skill is about doing the work, not describing it. When a user asks you to set up evals for their app, you should be reading their code, editing their files, running commands, and producing a working test pipeline — not writing a plan for them to follow later.

The loop is: understand the app → instrument it → write the test file → build a dataset → run the tests → investigate failures → iterate. In practice the stages blur and you'll be going back and forth, but this ordering helps: write all the files (instrumentation, test file, MEMORY.md) before running any commands. That way your work survives even if an execution step hits a snag.

---

## Stage 1: Understand the Application

Before touching any code, spend time actually reading the source. The code will tell you more than asking the user would, and it puts you in a much better position to make good decisions about what and how to evaluate.

What you're looking for:

- The entry point and the main function(s) that do the LLM-powered work
- Every place external data flows into a prompt — user input, retrieved documents, database results, API responses, system prompts
- The final output (what the user sees or what gets returned)
- Any intermediate steps that might be worth evaluating separately (e.g. a retrieval step)

Write your findings down in a `MEMORY.md` file in the project (or `.claude/memory/eval-notes.md`) as you go. Include:

- How to run the app
- Which function(s) you'll instrument and what their `eval_input` / `eval_output` will look like
- The use cases the app handles
- Your eval plan: what to measure and which evaluators make sense

This file is how your understanding persists across sessions. Keep it updated as you learn more.

If something is genuinely unclear from the code, ask the user — but most questions answer themselves once you've read the code carefully.

---

## Stage 2: Decide What to Evaluate

Now that you understand the app, you can make thoughtful choices about what to measure:

- **What quality dimension matters most?** Factual accuracy for QA apps, output format for structured extraction, relevance for RAG, safety for user-facing text.
- **Which span to evaluate:** the whole pipeline (`root`) or just the LLM call (`last_llm_call`)? If you're debugging retrieval, you might evaluate at a different point than if you're checking final answer quality.
- **Which evaluators fit:** see `references/pixie-api.md` → Evaluators. For factual QA: `FactualityEval`. For structured output: `ValidJSONEval` / `JSONDiffEval`. For RAG pipelines: `ContextRelevancyEval` / `FaithfulnessEval`.
- **Pass criteria:** `ScoreThreshold(threshold=0.7, pct=0.8)` means 80% of cases must score ≥ 0.7. Think about what "good enough" looks like for this app.
- **Expected outputs:** `FactualityEval` needs them. Format evaluators usually don't.

Update your MEMORY.md with the plan before writing any code.

---

## Stage 3: Instrument the Application

Edit the app's source files to add pixie instrumentation. The goal is to make every run capture its inputs and outputs as observable spans, so you can later replay those runs as eval cases.

### Add `enable_storage()` at startup

Somewhere in the app's entry point — main function or module top-level — call:

```python
from pixie import enable_storage
enable_storage()  # creates SQLite DB, registers handler — idempotent
```

This is what actually persists traces to disk. Without it, `@observe` decorators will still fire but nothing gets saved.

### Wrap the function(s) you want to evaluate

`@observe` on a function captures all its kwargs as `eval_input` and its return value as `eval_output`:

```python
import pixie.instrumentation as px

@px.observe(name="answer_question")
def answer_question(question: str, context: str) -> str:
    ...
```

For more control, use the context manager:

```python
with px.start_observation(input={"question": question, "context": context}, name="answer_question") as obs:
    result = run_pipeline(question, context)
    obs.set_output(result)
    obs.set_metadata("retrieved_chunks", len(chunks))
```

Wrap at the outermost boundary that represents one "test case" — for a RAG app that's probably `answer_question(question, context)`, not the internal LLM call. The dataset items will have the same shape as whatever this function receives and returns.

After instrumentation, call `px.flush()` at the end of runs to make sure all spans are written before you try to save them to a dataset.

---

## Stage 4: Write the Eval Test File

Write the test file before building the dataset. This might seem backwards, but it forces you to decide what you're actually measuring before you start collecting data — otherwise the data collection has no direction.

Create `tests/test_<feature>.py`. The pattern is: a `runnable` adapter that calls your app function, plus an async test function that calls `assert_dataset_pass`:

```python
from pixie import enable_storage
from pixie.evals import assert_dataset_pass, FactualityEval, ScoreThreshold
from pixie.evals import last_llm_call  # or: from pixie.evals import root

from myapp import answer_question


def runnable(eval_input):
    """Replays one dataset item through the app. enable_storage() here ensures traces are captured."""
    enable_storage()
    answer_question(**eval_input)  # or answer_question(eval_input) if it's a plain string


async def test_factuality():
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name="<dataset-name>",
        evaluators=[FactualityEval()],
        pass_criteria=ScoreThreshold(threshold=0.7, pct=0.8),
        from_trace=last_llm_call,   # tells the harness which span's output to evaluate
    )
```

Note that `enable_storage()` belongs inside the `runnable`, not at module level in the test file — it needs to fire on each invocation so the trace is captured for that specific run.

The test runner is `pixie-test` (not `pytest` or `python -m pixie test` — those won't set up the async environment correctly):

```bash
pixie-test                     # run all test_*.py in current directory
pixie-test tests/              # specify path
pixie-test -k factuality       # filter by name
pixie-test -v                  # verbose: shows per-case scores and reasoning
```

---

## Stage 5: Build the Dataset

Create the dataset first, then populate it by running the app:

```bash
pixie dataset create <dataset-name>
pixie dataset list   # verify it exists
```

### Option A: Capture from real runs (the natural starting point)

Run the app with representative inputs, then save each trace to the dataset:

```bash
# Run the app (enable_storage() must be active)
python -c "from myapp import main; main('What is the capital of France?')"

# Save the root span to the dataset
pixie dataset save <dataset-name>

# Or specifically save the last LLM call:
pixie dataset save <dataset-name> --select last_llm_call

# Add context:
pixie dataset save <dataset-name> --notes "basic geography question"

# Attach expected output for evaluators like FactualityEval:
echo '"Paris"' | pixie dataset save <dataset-name> --expected-output
```

Try to cover the range of inputs you actually care about: normal cases, edge cases, things the app might plausibly get wrong (empty input, ambiguous queries, no-answer cases).

### Option B: Build programmatically

When you want to bulk-load items or add expected outputs directly:

```python
from pixie.dataset.store import DatasetStore
from pixie.storage.evaluable import Evaluable

store = DatasetStore()
store.create("<dataset-name>")
store.append("<dataset-name>", Evaluable(
    eval_input={"question": "What is the capital of France?", "context": "Paris is the capital..."},
    eval_output="Paris is the capital of France.",
    expected_output="Paris",
))
```

---

## Stage 6: Run the Tests

```bash
pixie-test tests/ -v
```

The `-v` flag shows per-case scores and reasoning, which makes it much easier to see what's passing and what isn't. Check that the pass rates look reasonable given your `ScoreThreshold`.

---

## Stage 7: Investigate Failures

When tests fail, the goal is to understand _why_, not to adjust thresholds until things pass.

```bash
pixie-test -v    # start here — shows score and reasoning per case
```

If you need to dig into a specific trace, look up the `trace_id` from the dataset:

```python
from pixie.dataset.store import DatasetStore
store = DatasetStore()
ds = store.get("<dataset-name>")
for i, item in enumerate(ds.items):
    print(i, item.eval_metadata)   # trace_id is here if saved via pixie dataset save
```

Then inspect the full span tree:

```python
import asyncio
from pixie.storage.store import ObservationStore

async def inspect(trace_id: str):
    store = ObservationStore()
    roots = await store.get_trace(trace_id)
    for root in roots:
        print(root.to_text())   # full span tree: inputs, outputs, LLM messages

asyncio.run(inspect("the-trace-id-here"))
```

Common patterns to look for:

| Symptom                          | Likely cause                                    |
| -------------------------------- | ----------------------------------------------- |
| Output is factually wrong        | Prompt or retrieved context is bad              |
| Output is right but score is low | Wrong `expected_output`, or criteria too strict |
| Score 0.0 with error details     | Evaluator crashed (missing API key, etc.)       |
| All cases fail at same point     | `@observe` is on the wrong function             |

Once you've diagnosed the issue, make a targeted change — to the code, prompt, dataset item, or pass criteria — and re-run. Always finish by giving the user the exact command to verify:

```bash
pixie-test tests/test_<feature>.py -v
```

---

## Memory Template

```markdown
## Project: <name>

### Entry point

`python chatbot.py` or `answer_question(question, context)` etc.

### Instrumented spans

- `answer_question(question, context)` — @observe wraps the full pipeline
  - eval_input: {"question": str, "context": str}
  - eval_output: str (the answer)

### Datasets

- `qa-golden-set`: N items, factual QA, includes expected_output

### Eval plan

- Evaluator: FactualityEval
- Pass criteria: ScoreThreshold(0.7, pct=0.8)
- Test file: tests/test_qa.py::test_factuality

### Known issues / findings

- ...
```

---

## Reference

See `references/pixie-api.md` for all CLI commands, evaluator signatures, and the Python dataset/store API.
