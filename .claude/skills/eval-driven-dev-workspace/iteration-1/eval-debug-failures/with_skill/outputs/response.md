# Investigating and Fixing qa-golden-set Test Failures

The message "Average score: 0.41, all >= 0.5: False" tells you the tests are failing, but not *which* cases or *why*. Here is a systematic process to go from that summary to a real fix.

---

## Step 1: Get per-case details with `-v`

Run `pixie-test` with the verbose flag:

```bash
pixie-test -v
```

This prints the full `EvalAssertionError` payload, which includes scores and reasoning for **every dataset item**. You will see something like:

```
FAILED tests/test_qa.py::test_factuality
EvalAssertionError: Pass criteria not met (average score: 0.41)

Case 0: score=0.85  PASS  reasoning="Correct capital named"
Case 1: score=0.20  FAIL  reasoning="Answer contradicts reference: says Berlin, expected Paris"
Case 2: score=0.55  PASS  reasoning="Mostly accurate"
Case 3: score=0.10  FAIL  reasoning="Output is empty"
Case 4: score=0.75  PASS  ...
```

Note the failing case indices (1 and 3 in this example) and their reasoning strings.

---

## Step 2: Find the trace for each failing case

Each dataset item stores metadata captured when the trace was saved. Open the dataset file directly or use the Python API:

```python
from pixie.dataset.store import DatasetStore

store = DatasetStore()
dataset = store.get("qa-golden-set")
for i, item in enumerate(dataset.items):
    trace_id = item.eval_metadata.get("trace_id")
    print(f"Case {i}: trace_id={trace_id}")
```

The `trace_id` links the dataset item back to the full execution trace stored in `pixie_observations.db`.

---

## Step 3: Inspect the full trace

Use `ObservationStore` to see exactly what the app received and produced:

```python
import asyncio
from pixie.storage.store import ObservationStore

async def inspect(trace_id: str):
    store = ObservationStore()
    roots = await store.get_trace(trace_id)
    for root in roots:
        print(root.to_text())   # pretty-prints the full span tree

asyncio.run(inspect("your-trace-id-here"))
```

`to_text()` shows every span in the tree: the outer `@observe` span (with `eval_input` and `eval_output`) and the LLM call spans (with exact prompts, completions, and token counts). This gives you the ground truth of what happened.

---

## Step 4: Diagnose the root cause

Look at the verbose output and the trace together. The most common causes are:

| Symptom | Likely cause |
|---|---|
| Low score + reasoning says "empty output" or "no answer" | App crashed or returned nothing for this input |
| Low score + reasoning says "answer contradicts reference" | Prompt is wrong, or retrieval returned bad context |
| Low score + reasoning says "expected output is vague" | The `expected_output` you saved is ambiguous or incorrect |
| All cases fail at similar scores | Pass criteria (`ScoreThreshold`) may be too strict for this evaluator |
| Only specific inputs fail | Input-specific issue — edge case the prompt can't handle |

---

## Step 5: Reproduce the failing case

Take the `eval_input` from the failing dataset item and run the app directly:

```python
from pixie import enable_storage
from my_app import answer_question

enable_storage()

# Use the exact input from the failing case
answer_question(question="...", context="...")
```

Add extra logging or intermediate `@observe` spans to see what the retrieval step returned or how the prompt was assembled.

---

## Step 6: Make a targeted fix

Based on your diagnosis, act on **one** of these:

- **Fix the prompt** — if the LLM is producing wrong answers, update your system prompt or few-shot examples, then re-run the tests.
- **Fix the retrieval** — if the context passed to the LLM is irrelevant, debug the retrieval pipeline.
- **Fix the dataset** — if `expected_output` was wrong or too strict, update it:
  ```python
  from pixie.dataset.store import DatasetStore
  from pixie.storage.evaluable import Evaluable

  store = DatasetStore()
  dataset = store.get("qa-golden-set")
  # Replace item at index 1 with corrected expected_output
  store.remove("qa-golden-set", index=1)
  store.append("qa-golden-set", Evaluable(
      eval_input=dataset.items[1].eval_input,
      eval_output=dataset.items[1].eval_output,
      expected_output="The corrected reference answer",
      eval_metadata=dataset.items[1].eval_metadata,
  ))
  ```
- **Relax the pass criteria** — if expectations were set too tight and the quality is actually acceptable, use `ScoreThreshold` with a lower threshold or allow a small fraction to fail:
  ```python
  await assert_dataset_pass(
      runnable=runnable,
      dataset_name="qa-golden-set",
      evaluators=[FactualityEval()],
      pass_criteria=ScoreThreshold(threshold=0.5, pct=0.8),  # 80% must pass, not 100%
  )
  ```

---

## Step 7: Re-run and compare

After your change, run the tests again:

```bash
pixie-test -v
```

Check:
- Did the previously failing cases improve?
- Did any passing cases regress?
- Is the average score now above threshold?

Keep cycling through steps 1–6 until all tests pass or you are satisfied with coverage and quality. When adding new test scenarios, add them to the dataset (`pixie dataset save`) rather than writing separate one-off test functions.

---

## Quick reference cheat-sheet

```bash
# See per-case scores and reasoning
pixie-test -v

# Re-run only the failing test
pixie-test -k factuality -v

# Inspect trace from Python
python - <<'EOF'
import asyncio
from pixie.storage.store import ObservationStore

async def main():
    store = ObservationStore()
    roots = await store.get_trace("PASTE-TRACE-ID-HERE")
    for r in roots:
        print(r.to_text())

asyncio.run(main())
EOF
```
