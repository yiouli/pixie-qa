"""Eval tests for extract_from_email.

Tests use pixie's assert_dataset_pass harness against the 'email-extraction'
dataset built by build_dataset.py.

Run with:
    pixie-test tests/
    pixie-test tests/ -v   # verbose: per-case scores and reasoning

Evaluators used (all heuristic — no LLM / API key required):
  1. valid_json_schema  — ValidJSONEval with a JSON Schema to ensure the output
                          has exactly the required keys with valid enum values.
  2. json_diff          — JSONDiffEval comparing actual output to expected_output,
                          scoring structural similarity field by field.
  3. required_keys      — Custom evaluator: checks that category, priority, and
                          summary are all present and non-empty strings.
  4. category_exact     — Custom evaluator: exact match on the 'category' field.
  5. priority_exact     — Custom evaluator: exact match on the 'priority' field.
"""

from __future__ import annotations

import os
import sys

# Ensure the pixie source package is importable.
PIXIE_ROOT = os.environ.get("PIXIE_ROOT", "/home/yiouli/repo/pixie-qa")
if PIXIE_ROOT not in sys.path:
    sys.path.insert(0, PIXIE_ROOT)

# Ensure the project root is importable so 'extractor' can be found.
PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from pixie import enable_storage
from pixie.evals import (
    Evaluation,
    JSONDiffEval,
    ScoreThreshold,
    ValidJSONEval,
    assert_dataset_pass,
    root,
)
from pixie.storage.evaluable import Evaluable

from extractor import extract_from_email  # the function under test

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATASET_DIR = os.path.join(PROJECT_DIR, "pixie_datasets")
DATASET_NAME = "email-extraction"

# ---------------------------------------------------------------------------
# JSON Schema for the extractor's output
# ---------------------------------------------------------------------------

EMAIL_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": ["billing", "technical", "account", "general"],
        },
        "priority": {
            "type": "string",
            "enum": ["low", "medium", "high"],
        },
        "summary": {
            "type": "string",
            "minLength": 5,
        },
    },
    "required": ["category", "priority", "summary"],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# Custom evaluators
# ---------------------------------------------------------------------------


async def required_keys_eval(evaluable: Evaluable, *, trace=None) -> Evaluation:
    """Check that category, priority, and summary are present and non-empty."""
    output = evaluable.eval_output
    if not isinstance(output, dict):
        return Evaluation(
            score=0.0,
            reasoning=f"Output is not a dict; got {type(output).__name__}",
        )
    missing = []
    for key in ("category", "priority", "summary"):
        val = output.get(key)
        if not val or not isinstance(val, str) or not val.strip():
            missing.append(key)
    if missing:
        return Evaluation(
            score=0.0,
            reasoning=f"Missing or empty required keys: {missing}",
        )
    return Evaluation(score=1.0, reasoning="All required keys present and non-empty.")


async def category_exact_eval(evaluable: Evaluable, *, trace=None) -> Evaluation:
    """Exact match on the 'category' field vs expected_output."""
    output = evaluable.eval_output
    expected = evaluable.expected_output
    if not isinstance(output, dict):
        return Evaluation(score=0.0, reasoning="Output is not a dict.")
    actual_cat = output.get("category")
    if isinstance(expected, dict):
        expected_cat = expected.get("category")
        if actual_cat == expected_cat:
            return Evaluation(score=1.0, reasoning=f"category='{actual_cat}' matches.")
        return Evaluation(
            score=0.0,
            reasoning=f"category mismatch: got '{actual_cat}', expected '{expected_cat}'.",
        )
    # No expected output — just validate it's a known enum value.
    valid = {"billing", "technical", "account", "general"}
    if actual_cat in valid:
        return Evaluation(score=1.0, reasoning=f"category='{actual_cat}' is a valid enum value.")
    return Evaluation(score=0.0, reasoning=f"category='{actual_cat}' is not a valid enum value.")


async def priority_exact_eval(evaluable: Evaluable, *, trace=None) -> Evaluation:
    """Exact match on the 'priority' field vs expected_output."""
    output = evaluable.eval_output
    expected = evaluable.expected_output
    if not isinstance(output, dict):
        return Evaluation(score=0.0, reasoning="Output is not a dict.")
    actual_pri = output.get("priority")
    if isinstance(expected, dict):
        expected_pri = expected.get("priority")
        if actual_pri == expected_pri:
            return Evaluation(score=1.0, reasoning=f"priority='{actual_pri}' matches.")
        return Evaluation(
            score=0.0,
            reasoning=f"priority mismatch: got '{actual_pri}', expected '{expected_pri}'.",
        )
    valid = {"low", "medium", "high"}
    if actual_pri in valid:
        return Evaluation(score=1.0, reasoning=f"priority='{actual_pri}' is a valid enum value.")
    return Evaluation(score=0.0, reasoning=f"priority='{actual_pri}' is not a valid enum value.")


# ---------------------------------------------------------------------------
# Runnable adapter
# ---------------------------------------------------------------------------


def runnable(eval_input):
    """Call extract_from_email with the stored eval_input dict.

    enable_storage() is called here so each test run has storage active,
    even when running the test file in isolation.
    """
    enable_storage()
    # eval_input captured by @observe is {"email_text": str}
    extract_from_email(**eval_input)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_valid_json_schema():
    """Output must be valid JSON matching the email-extraction schema."""
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name=DATASET_NAME,
        dataset_dir=DATASET_DIR,
        evaluators=[ValidJSONEval(schema=EMAIL_EXTRACTION_SCHEMA)],
        pass_criteria=ScoreThreshold(threshold=1.0, pct=1.0),
        from_trace=root,
    )


async def test_required_keys_present():
    """Output must contain category, priority, and summary as non-empty strings."""
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name=DATASET_NAME,
        dataset_dir=DATASET_DIR,
        evaluators=[required_keys_eval],
        pass_criteria=ScoreThreshold(threshold=1.0, pct=1.0),
        from_trace=root,
    )


async def test_json_structure_diff():
    """Structural similarity vs expected output (category + priority must match)."""
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name=DATASET_NAME,
        dataset_dir=DATASET_DIR,
        evaluators=[JSONDiffEval()],
        # category and priority are exact-enum fields; summary may vary slightly.
        # Require ≥ 0.6 avg structural similarity across 80% of cases.
        pass_criteria=ScoreThreshold(threshold=0.6, pct=0.8),
        from_trace=root,
    )


async def test_category_classification():
    """Category field must match the expected label for every item."""
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name=DATASET_NAME,
        dataset_dir=DATASET_DIR,
        evaluators=[category_exact_eval],
        pass_criteria=ScoreThreshold(threshold=1.0, pct=1.0),
        from_trace=root,
    )


async def test_priority_classification():
    """Priority field must match the expected label for at least 80% of items."""
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name=DATASET_NAME,
        dataset_dir=DATASET_DIR,
        evaluators=[priority_exact_eval],
        pass_criteria=ScoreThreshold(threshold=1.0, pct=0.8),
        from_trace=root,
    )
