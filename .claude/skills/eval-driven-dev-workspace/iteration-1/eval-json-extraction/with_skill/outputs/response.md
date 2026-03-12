# Eval-Driven Testing for JSON Extraction with pixie

This guide walks you through converting your `test_extraction.py` from "eyeballing output" to proper, automated eval-based tests using pixie. Your extraction function should produce JSON with `category`, `priority`, and `summary` fields from a customer support email.

---

## Stage 1: Understand Your Application

Your app takes a customer support email (text) as input, calls OpenAI, and returns a structured JSON object like:

```json
{
  "category": "billing",
  "priority": "high",
  "summary": "Customer was charged twice for the same order."
}
```

The key LLM call is the extraction step. That's what we want to evaluate.

---

## Stage 2: Evaluation Plan

For JSON extraction, the key quality dimensions are:

| Concern | Evaluator |
|---|---|
| Output is valid, parseable JSON | `ValidJSONEval(schema=...)` |
| Required fields are present | Custom evaluator |
| Field values are semantically correct | `FactualityEval` (LLM-as-judge) |

We'll run all three evaluators together on a dataset of test emails.

---

## Stage 3: Instrument Your Code

Add `@observe` around your extraction function so pixie can capture inputs and outputs. Add `enable_storage()` at startup.

**Before (your current code, approximately):**

```python
import openai

def extract_from_email(email_text: str) -> dict:
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Extract category, priority, and summary from the email. Return JSON only."},
            {"role": "user", "content": email_text},
        ],
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content
```

**After (instrumented):**

```python
import openai
from pixie import enable_storage
import pixie.instrumentation as px

enable_storage()  # call once at module load or app startup

@px.observe(name="extract_from_email")
def extract_from_email(email_text: str) -> dict:
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Extract category, priority, and summary from the email. Return JSON only."},
            {"role": "user", "content": email_text},
        ],
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content

# After a run, flush so the trace is written to the DB
# px.flush()
```

Key points:
- `@px.observe(name="extract_from_email")` wraps the function. pixie will record `eval_input = {"email_text": <the email>}` and `eval_output = <the returned JSON string>`.
- `enable_storage()` is idempotent — safe to call multiple times or at import time.
- Call `px.flush()` after running the function before using any CLI commands.

---

## Stage 4: Build a Dataset

### Step 4a: Create the dataset

```bash
pixie dataset create email-extraction
pixie dataset list   # verify it appears
```

### Step 4b: Capture real runs

Modify your existing `test_extraction.py` temporarily to capture traces:

```python
# test_extraction.py (temporary capture script)
from pixie import enable_storage
import pixie.instrumentation as px
from my_extraction_module import extract_from_email  # your module

enable_storage()

test_emails = [
    "Hi, I was charged twice for order #12345. Please refund immediately.",
    "I can't log into my account. I've tried resetting the password three times.",
    "Just wanted to say your product is amazing, keep it up!",
    "My package was supposed to arrive yesterday but tracking shows it's still in transit.",
    "How do I cancel my subscription?",
]

for email in test_emails:
    extract_from_email(email_text=email)
    px.flush()
    # Now save the trace to the dataset:
    # Run: pixie dataset save email-extraction --notes "<brief description>"
```

After each `px.flush()`, run the CLI save command in a separate terminal:

```bash
pixie dataset save email-extraction --notes "billing double-charge complaint"
pixie dataset save email-extraction --notes "login issue"
# ... etc
```

**Tip:** To attach expected outputs (recommended for `FactualityEval`), pipe expected JSON as the expected output:

```bash
echo '{"category": "billing", "priority": "high", "summary": "Customer was charged twice for order #12345."}' \
  | pixie dataset save email-extraction --expected-output --notes "billing double-charge complaint"
```

### Step 4c: (Alternative) Build the dataset programmatically

If you already know the expected outputs, skip the capture loop and build the dataset directly:

```python
# build_dataset.py
from pixie.dataset.store import DatasetStore
from pixie.storage.evaluable import Evaluable
from my_extraction_module import extract_from_email
from pixie import enable_storage
import pixie.instrumentation as px

enable_storage()

test_cases = [
    {
        "email_text": "I was charged twice for order #12345. Please refund.",
        "expected_output": '{"category": "billing", "priority": "high", "summary": "Customer charged twice for order #12345, requesting refund."}',
    },
    {
        "email_text": "I cannot log into my account after the password reset.",
        "expected_output": '{"category": "account", "priority": "medium", "summary": "Customer cannot log in after password reset."}',
    },
    {
        "email_text": "Your product is amazing, keep it up!",
        "expected_output": '{"category": "compliment", "priority": "low", "summary": "Customer complimenting the product."}',
    },
    {
        "email_text": "My package is late, tracking shows it is still in transit.",
        "expected_output": '{"category": "shipping", "priority": "medium", "summary": "Package delayed, still in transit past expected delivery date."}',
    },
    {
        "email_text": "How do I cancel my subscription?",
        "expected_output": '{"category": "billing", "priority": "low", "summary": "Customer asking how to cancel their subscription."}',
    },
]

store = DatasetStore()
store.create("email-extraction")

for case in test_cases:
    store.append("email-extraction", Evaluable(
        eval_input={"email_text": case["email_text"]},
        expected_output=case["expected_output"],
    ))

print("Dataset created with", len(test_cases), "items.")
```

---

## Stage 5: Write the Eval Tests

Create `test_extraction.py` (replacing your old version):

```python
# test_extraction.py
import json
import asyncio
from pixie import enable_storage
from pixie.evals import (
    assert_dataset_pass,
    Evaluation,
    ScoreThreshold,
    ValidJSONEval,
    FactualityEval,
    root,
)
from pixie.storage.evaluable import Evaluable
from my_extraction_module import extract_from_email  # adjust import


def runnable(eval_input):
    """Adapter: called by pixie for each dataset item."""
    enable_storage()
    extract_from_email(**eval_input)


# ── Custom evaluator: checks all required fields are present ──────────────────

async def has_required_fields(evaluable: Evaluable, *, trace=None) -> Evaluation:
    """Checks that the JSON output contains category, priority, and summary."""
    output = evaluable.eval_output
    if output is None:
        return Evaluation(score=0.0, reasoning="No output produced.")
    try:
        data = json.loads(output) if isinstance(output, str) else output
    except (json.JSONDecodeError, TypeError):
        return Evaluation(score=0.0, reasoning="Output is not valid JSON.")

    required = {"category", "priority", "summary"}
    missing = required - set(data.keys())
    if missing:
        return Evaluation(
            score=0.0,
            reasoning=f"Missing required fields: {missing}",
        )
    return Evaluation(score=1.0, reasoning="All required fields present.")


# ── Test 1: Structure check (no LLM judge needed) ─────────────────────────────

async def test_extraction_structure():
    """Every extraction must produce valid JSON with all required fields."""
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name="email-extraction",
        evaluators=[
            ValidJSONEval(),       # is the output parseable JSON?
            has_required_fields,   # does it have category, priority, summary?
        ],
        pass_criteria=ScoreThreshold(threshold=1.0, pct=1.0),  # must be perfect
        from_trace=root,
    )


# ── Test 2: Semantic quality (LLM-as-judge, requires expected_output) ─────────

async def test_extraction_quality():
    """Extracted values should be semantically accurate vs. expected outputs."""
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name="email-extraction",
        evaluators=[
            FactualityEval(),   # compares eval_output to expected_output
        ],
        pass_criteria=ScoreThreshold(threshold=0.7, pct=0.8),  # 80% must score >= 0.7
        from_trace=root,
    )
```

Run the tests:

```bash
pixie-test                   # run all tests
pixie-test -k structure      # run only test_extraction_structure
pixie-test -k quality        # run only test_extraction_quality
pixie-test -v                # verbose: see scores and reasoning for each case
```

---

## Stage 6: Investigate Failures

If a test fails, `pixie-test -v` will show you the score and reasoning for every dataset item. For example:

```
FAILED test_extraction.py::test_extraction_structure
  Item 3: has_required_fields score=0.0 — Missing required fields: {'priority'}
```

To dig deeper into a specific trace, find the `trace_id` from `eval_metadata` and inspect the full span tree:

```python
import asyncio
from pixie.storage.store import ObservationStore

async def inspect(trace_id: str):
    store = ObservationStore()
    roots = await store.get_trace(trace_id)
    for root in roots:
        print(root.to_text())

asyncio.run(inspect("your-trace-id-here"))
```

This shows you the full prompt sent to OpenAI, the raw response, and all intermediate spans — making it easy to identify whether the problem is in the prompt, the response parsing, or the model's behavior.

---

## Summary: Files to Create

| File | Purpose |
|---|---|
| `my_extraction_module.py` | Your extraction code, instrumented with `@px.observe` |
| `build_dataset.py` | One-time script to populate `pixie_datasets/email-extraction.json` |
| `test_extraction.py` | Eval tests — replaces your old eyeballing script |

---

## Quick Reference: The Eval Loop

```
1. edit prompt or code
2. python build_dataset.py      (or pixie dataset save ... after manual runs)
3. pixie-test -v
4. look at failures → go to 1
```

Once `pixie-test` reports all green at your thresholds, you have confidence that the extraction is working correctly across your test cases — not just for the one email you happened to try.
