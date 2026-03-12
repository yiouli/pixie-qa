# Converting test_extraction.py to Eval-Based Tests with Pixie

## Overview

Pixie is a QA framework for LLM applications that provides instrumentation, trace storage, and an evaluation harness. To convert your `test_extraction.py` from manual eyeballing to proper evals, you'll follow this pattern:

1. Instrument your extraction function so pixie can capture traces
2. Build a dataset of test emails with expected outputs
3. Write evaluators that check the JSON fields
4. Use `assert_pass` or `assert_dataset_pass` to run and assert results

---

## Step 1: Instrument Your Extraction Function

Wrap your OpenAI call with pixie instrumentation so the framework can capture inputs and outputs:

```python
import pixie.instrumentation as px
from pixie import enable_storage

# One-time setup — call this at module or app startup
enable_storage()
px.init()

def extract_from_email(email_text: str) -> dict:
    with px.start_observation(input=email_text, name="email_extraction") as observation:
        # Your existing OpenAI call here
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Extract a JSON object with fields: category, priority, summary."},
                {"role": "user", "content": email_text},
            ],
            response_format={"type": "json_object"},
        )
        result = response.choices[0].message.content  # raw JSON string
        observation.set_output(result)
    return result
```

The `start_observation` context manager records the input email and the output JSON string as a trace that pixie can evaluate.

---

## Step 2: Define Your Evaluators

For JSON extraction, two evaluators are most important:

### 2a. Schema Validation (Heuristic — No LLM Required)

Use `ValidJSONEval` to check that the output is valid JSON with the required fields:

```python
import json
from pixie.evals import Evaluation
from pixie.storage.evaluable import Evaluable

async def has_required_fields(evaluable: Evaluable, *, trace=None) -> Evaluation:
    """Check that output JSON contains category, priority, and summary."""
    try:
        data = json.loads(evaluable.eval_output)
    except (json.JSONDecodeError, TypeError):
        return Evaluation(score=0.0, reasoning="Output is not valid JSON")

    required = {"category", "priority", "summary"}
    missing = required - set(data.keys())
    if missing:
        return Evaluation(
            score=0.0,
            reasoning=f"Missing required fields: {missing}",
        )
    return Evaluation(score=1.0, reasoning="All required fields present")
```

### 2b. Field Value Correctness (LLM-as-Judge)

For checking that the extracted values are actually correct, use `FactualityEval` or a custom LLM judge:

```python
from pixie.evals import FactualityEval

# Built-in LLM-as-judge: checks if output is factually consistent with expected
factuality_evaluator = FactualityEval(expected="...")
```

Or write a custom evaluator that checks specific field values:

```python
async def correct_category(evaluable: Evaluable, *, trace=None) -> Evaluation:
    """Check that 'category' field matches the expected value."""
    try:
        data = json.loads(evaluable.eval_output)
        expected = json.loads(evaluable.expected_output) if evaluable.expected_output else {}
    except (json.JSONDecodeError, TypeError):
        return Evaluation(score=0.0, reasoning="Could not parse JSON")

    actual_category = data.get("category", "").strip().lower()
    expected_category = expected.get("category", "").strip().lower()

    if actual_category == expected_category:
        return Evaluation(score=1.0, reasoning=f"Category '{actual_category}' matches expected")
    return Evaluation(
        score=0.0,
        reasoning=f"Category mismatch: got '{actual_category}', expected '{expected_category}'",
    )
```

### 2c. Use Built-in JSONDiffEval for Structural Comparison

Pixie also ships `JSONDiffEval` for structural JSON comparison:

```python
from pixie.evals import JSONDiffEval

# Compares JSON structure and values; score reflects similarity
json_diff = JSONDiffEval(expected='{"category": "billing", "priority": "high", "summary": "..."}')
```

---

## Step 3: Build a Dataset

Create a reusable dataset of test emails with expected outputs:

```python
from pixie.dataset import DatasetStore
from pixie.storage.evaluable import Evaluable
import json

store = DatasetStore()

store.create("email-extraction-golden", items=[
    Evaluable(
        eval_input="Hi, my invoice is wrong and I was charged twice this month. Please fix ASAP.",
        expected_output=json.dumps({
            "category": "billing",
            "priority": "high",
            "summary": "Customer was double-charged and requests urgent correction",
        }),
    ),
    Evaluable(
        eval_input="I forgot my password and can't log in. Not urgent, just whenever.",
        expected_output=json.dumps({
            "category": "account",
            "priority": "low",
            "summary": "Customer needs password reset",
        }),
    ),
    Evaluable(
        eval_input="Your product is amazing! Just wanted to share some feedback.",
        expected_output=json.dumps({
            "category": "feedback",
            "priority": "low",
            "summary": "Customer submitted positive product feedback",
        }),
    ),
])
```

You only need to create this dataset once. After that, tests load it by name.

---

## Step 4: Write the Test File

Replace your `test_extraction.py` with proper eval-based tests:

```python
# test_extraction.py
import asyncio
import json
import pytest
import pixie.instrumentation as px
from pixie import enable_storage
from pixie.evals import (
    assert_pass,
    assert_dataset_pass,
    Evaluation,
    ScoreThreshold,
    ValidJSONEval,
    JSONDiffEval,
)
from pixie.storage.evaluable import Evaluable

# --- Setup ---

enable_storage()
px.init()


# --- The function under test ---

def extract_from_email(email_text: str) -> str:
    """Extract structured JSON from a customer support email."""
    with px.start_observation(input=email_text, name="email_extraction") as observation:
        # Replace with your actual OpenAI call
        from openai import OpenAI
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract a JSON object from this customer support email. "
                        "Include exactly these fields: category (string), "
                        "priority ('low', 'medium', or 'high'), and summary (string)."
                    ),
                },
                {"role": "user", "content": email_text},
            ],
            response_format={"type": "json_object"},
        )
        result = response.choices[0].message.content
        observation.set_output(result)
    return result


# --- Custom evaluators ---

async def has_required_fields(evaluable: Evaluable, *, trace=None) -> Evaluation:
    """Heuristic: output must be valid JSON with category, priority, summary."""
    try:
        data = json.loads(evaluable.eval_output)
    except (json.JSONDecodeError, TypeError):
        return Evaluation(score=0.0, reasoning="Output is not valid JSON")

    required = {"category", "priority", "summary"}
    missing = required - set(data.keys())
    if missing:
        return Evaluation(score=0.0, reasoning=f"Missing fields: {missing}")

    return Evaluation(score=1.0, reasoning="All required fields present")


async def valid_priority_value(evaluable: Evaluable, *, trace=None) -> Evaluation:
    """Heuristic: priority field must be one of the allowed values."""
    try:
        data = json.loads(evaluable.eval_output)
    except (json.JSONDecodeError, TypeError):
        return Evaluation(score=0.0, reasoning="Output is not valid JSON")

    allowed = {"low", "medium", "high"}
    priority = data.get("priority", "").strip().lower()
    if priority in allowed:
        return Evaluation(score=1.0, reasoning=f"Priority '{priority}' is valid")
    return Evaluation(
        score=0.0,
        reasoning=f"Invalid priority '{priority}'. Must be one of: {allowed}",
    )


async def category_matches_expected(evaluable: Evaluable, *, trace=None) -> Evaluation:
    """Check that extracted category matches expected."""
    if not evaluable.expected_output:
        return Evaluation(score=1.0, reasoning="No expected output to compare")
    try:
        actual = json.loads(evaluable.eval_output)
        expected = json.loads(evaluable.expected_output)
    except (json.JSONDecodeError, TypeError):
        return Evaluation(score=0.0, reasoning="Could not parse JSON")

    actual_cat = actual.get("category", "").strip().lower()
    expected_cat = expected.get("category", "").strip().lower()

    if actual_cat == expected_cat:
        return Evaluation(score=1.0, reasoning=f"Category matches: '{actual_cat}'")
    return Evaluation(
        score=0.0,
        reasoning=f"Category mismatch: got '{actual_cat}', expected '{expected_cat}'",
    )


# --- Tests ---

@pytest.mark.asyncio
async def test_extraction_produces_valid_schema():
    """Every email must produce JSON with the three required fields."""
    test_emails = [
        "My invoice is wrong, I was charged twice.",
        "I can't log in to my account.",
        "Your product is great, just giving feedback.",
    ]
    await assert_pass(
        runnable=extract_from_email,
        eval_inputs=test_emails,
        evaluators=[has_required_fields, valid_priority_value],
        # All inputs must pass both evaluators
        pass_criteria=ScoreThreshold(threshold=1.0, pct=1.0),
    )


@pytest.mark.asyncio
async def test_extraction_matches_golden_dataset():
    """Categories must match the curated golden dataset."""
    await assert_dataset_pass(
        runnable=extract_from_email,
        dataset_name="email-extraction-golden",
        evaluators=[has_required_fields, category_matches_expected],
        pass_criteria=ScoreThreshold(threshold=1.0, pct=1.0),
    )


@pytest.mark.asyncio
async def test_extraction_passes_at_80_pct():
    """Lenient test: 80% of samples must have correct structure."""
    test_emails = [
        "Billing issue — I was charged the wrong amount.",
        "Account locked out.",
        "Feature request: dark mode please.",
        "Delivery is late, very upset.",
        "Just wanted to say thanks!",
    ]
    await assert_pass(
        runnable=extract_from_email,
        eval_inputs=test_emails,
        evaluators=[has_required_fields],
        pass_criteria=ScoreThreshold(threshold=1.0, pct=0.8),  # 80% must pass
    )
```

---

## Step 5: Run the Tests

```bash
# Run with pytest directly
pytest test_extraction.py -v

# Or use the pixie CLI test runner
pixie-test test_extraction.py -v

# Run a specific test
pytest test_extraction.py::test_extraction_produces_valid_schema -v
```

---

## Workflow Summary

| Step | What to do | Pixie API |
|------|-----------|-----------|
| Instrument | Wrap your function with `start_observation` | `px.start_observation()` |
| Store traces | Enable one-line persistence | `enable_storage()` |
| Evaluate structurally | Check fields exist and are valid | `has_required_fields` (custom) or `ValidJSONEval` |
| Evaluate values | Compare against golden outputs | `JSONDiffEval`, `FactualityEval`, or custom |
| Manage test cases | Persist and reuse golden examples | `DatasetStore`, `Evaluable` |
| Assert in tests | Run batch evals with pass/fail | `assert_pass`, `assert_dataset_pass` |

---

## Key Decisions to Make

**Which evaluators to use:**

- `has_required_fields` (custom, heuristic): checks the schema — always do this first, it's free and fast
- `valid_priority_value` (custom, heuristic): enum validation — zero cost, catches bad values
- `category_matches_expected` (custom, heuristic): exact field match against golden labels
- `JSONDiffEval`: pixie built-in for structural similarity — useful when you have expected outputs but want partial credit
- `FactualityEval`: LLM judge for semantic correctness of the summary field — more expensive but catches paraphrasing/hallucination

**Pass criteria:**

- For schema checks: `ScoreThreshold(threshold=1.0, pct=1.0)` — every output must have all fields
- For semantic/content checks: consider `ScoreThreshold(threshold=0.7, pct=0.8)` to tolerate minor variation

**Expected outputs:**

Store expected outputs in a dataset (`DatasetStore`) rather than hardcoding them in tests. This keeps test code clean and makes it easy to grow the golden set over time using `pixie dataset save`.

---

## Saving New Golden Examples via CLI

After running your app against a real email, you can capture the trace and add it to your dataset:

```bash
# Save the most recent trace's root span to the golden dataset
pixie dataset save email-extraction-golden

# Or pipe in an expected output at the same time
echo '{"category":"billing","priority":"high","summary":"Double charge issue"}' | \
  pixie dataset save email-extraction-golden --expected-output
```

This trace-to-dataset workflow means your golden set grows organically as you encounter real-world examples.
