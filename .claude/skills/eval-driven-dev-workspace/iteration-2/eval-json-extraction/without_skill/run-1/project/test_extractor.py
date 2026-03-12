"""Eval-based tests for extract_from_email.

Run with pytest (requires the pixie_datasets/ directory to exist — build it
first with `python build_dataset.py`):

    pytest test_extractor.py -v

Or with the pixie CLI:

    pixie-test test_extractor.py -v

Environment variables required for the app under test:
    OPENAI_API_KEY  — used by extractor.py when calling GPT-4o-mini

The JSON-structure checks are heuristic (no LLM required), so they work
without an OpenAI key as long as the extractor itself is run in isolation or
mocked.
"""

import json
import sys

import pytest

sys.path.insert(0, "/home/yiouli/repo/pixie-qa")

import pixie.instrumentation as px
from pixie.evals import (
    Evaluation,
    assert_dataset_pass,
    assert_pass,
    ScoreThreshold,
)
from pixie.evals import ValidJSONEval, JSONDiffEval
from pixie.storage.evaluable import Evaluable

from extractor import extract_from_email

# ---------------------------------------------------------------------------
# Helper: wrap the plain function so pixie's eval harness can call it
# (assert_pass / assert_dataset_pass expect a callable that takes a single
#  positional argument).
# ---------------------------------------------------------------------------

def run_extractor(email_text: str):
    """Thin wrapper so the harness receives a single-arg callable."""
    return extract_from_email(email_text)


# ---------------------------------------------------------------------------
# Custom evaluators (heuristic — no LLM required)
# ---------------------------------------------------------------------------

VALID_CATEGORIES = {"billing", "technical", "account", "general"}
VALID_PRIORITIES = {"low", "medium", "high"}


async def has_required_keys(evaluable: Evaluable, *, trace=None) -> Evaluation:
    """Check that the output dict contains category, priority, and summary."""
    output = evaluable.eval_output
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except json.JSONDecodeError:
            return Evaluation(score=0.0, reasoning="Output is not valid JSON")

    if not isinstance(output, dict):
        return Evaluation(score=0.0, reasoning=f"Expected dict, got {type(output).__name__}")

    missing = [k for k in ("category", "priority", "summary") if k not in output]
    if missing:
        return Evaluation(
            score=0.0,
            reasoning=f"Missing required keys: {missing}",
            details={"missing_keys": missing},
        )
    return Evaluation(score=1.0, reasoning="All required keys present")


async def has_valid_category(evaluable: Evaluable, *, trace=None) -> Evaluation:
    """Check that 'category' is one of the allowed values."""
    output = evaluable.eval_output
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except json.JSONDecodeError:
            return Evaluation(score=0.0, reasoning="Output is not valid JSON")

    category = output.get("category") if isinstance(output, dict) else None
    if category in VALID_CATEGORIES:
        return Evaluation(score=1.0, reasoning=f"Valid category: {category!r}")
    return Evaluation(
        score=0.0,
        reasoning=f"Invalid category {category!r}; expected one of {sorted(VALID_CATEGORIES)}",
        details={"category": category},
    )


async def has_valid_priority(evaluable: Evaluable, *, trace=None) -> Evaluation:
    """Check that 'priority' is one of the allowed values."""
    output = evaluable.eval_output
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except json.JSONDecodeError:
            return Evaluation(score=0.0, reasoning="Output is not valid JSON")

    priority = output.get("priority") if isinstance(output, dict) else None
    if priority in VALID_PRIORITIES:
        return Evaluation(score=1.0, reasoning=f"Valid priority: {priority!r}")
    return Evaluation(
        score=0.0,
        reasoning=f"Invalid priority {priority!r}; expected one of {sorted(VALID_PRIORITIES)}",
        details={"priority": priority},
    )


async def has_non_empty_summary(evaluable: Evaluable, *, trace=None) -> Evaluation:
    """Check that 'summary' is a non-empty string."""
    output = evaluable.eval_output
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except json.JSONDecodeError:
            return Evaluation(score=0.0, reasoning="Output is not valid JSON")

    summary = output.get("summary") if isinstance(output, dict) else None
    if isinstance(summary, str) and summary.strip():
        return Evaluation(score=1.0, reasoning="Summary is a non-empty string")
    return Evaluation(
        score=0.0,
        reasoning=f"Summary is missing or empty: {summary!r}",
        details={"summary": summary},
    )


async def category_matches_expected(evaluable: Evaluable, *, trace=None) -> Evaluation:
    """Check that the predicted category matches the expected category."""
    output = evaluable.eval_output
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except json.JSONDecodeError:
            return Evaluation(score=0.0, reasoning="Output is not valid JSON")

    expected_raw = evaluable.expected_output
    if not expected_raw:
        return Evaluation(score=1.0, reasoning="No expected output — skipping category check")
    if isinstance(expected_raw, str):
        try:
            expected = json.loads(expected_raw)
        except json.JSONDecodeError:
            return Evaluation(score=0.0, reasoning="expected_output is not valid JSON")
    else:
        expected = expected_raw

    predicted_cat = output.get("category") if isinstance(output, dict) else None
    expected_cat = expected.get("category") if isinstance(expected, dict) else None

    if predicted_cat == expected_cat:
        return Evaluation(score=1.0, reasoning=f"Category matches: {predicted_cat!r}")
    return Evaluation(
        score=0.0,
        reasoning=f"Category mismatch: got {predicted_cat!r}, expected {expected_cat!r}",
        details={"predicted": predicted_cat, "expected": expected_cat},
    )


async def priority_matches_expected(evaluable: Evaluable, *, trace=None) -> Evaluation:
    """Check that the predicted priority matches the expected priority."""
    output = evaluable.eval_output
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except json.JSONDecodeError:
            return Evaluation(score=0.0, reasoning="Output is not valid JSON")

    expected_raw = evaluable.expected_output
    if not expected_raw:
        return Evaluation(score=1.0, reasoning="No expected output — skipping priority check")
    if isinstance(expected_raw, str):
        try:
            expected = json.loads(expected_raw)
        except json.JSONDecodeError:
            return Evaluation(score=0.0, reasoning="expected_output is not valid JSON")
    else:
        expected = expected_raw

    predicted_pri = output.get("priority") if isinstance(output, dict) else None
    expected_pri = expected.get("priority") if isinstance(expected, dict) else None

    if predicted_pri == expected_pri:
        return Evaluation(score=1.0, reasoning=f"Priority matches: {predicted_pri!r}")
    return Evaluation(
        score=0.0,
        reasoning=f"Priority mismatch: got {predicted_pri!r}, expected {expected_pri!r}",
        details={"predicted": predicted_pri, "expected": expected_pri},
    )


# ---------------------------------------------------------------------------
# Test: JSON structure only (no expected_output comparison)
# These tests verify the model always returns a well-formed response.
# ---------------------------------------------------------------------------

# Inline eval_inputs — same three emails used in the original ad-hoc test.
_STRUCTURE_INPUTS = [
    "Hi, my subscription was charged twice this month. Please refund the duplicate charge ASAP.",
    "The app keeps crashing when I try to upload files larger than 10MB. This is urgent.",
    "Can you tell me how to reset my password? I can't find the option in settings.",
]


@pytest.mark.asyncio
async def test_output_has_required_keys():
    """Every response must contain category, priority, and summary."""
    await assert_pass(
        runnable=run_extractor,
        eval_inputs=_STRUCTURE_INPUTS,
        evaluators=[has_required_keys],
    )


@pytest.mark.asyncio
async def test_category_is_valid_enum():
    """category must be one of the four allowed values."""
    await assert_pass(
        runnable=run_extractor,
        eval_inputs=_STRUCTURE_INPUTS,
        evaluators=[has_valid_category],
    )


@pytest.mark.asyncio
async def test_priority_is_valid_enum():
    """priority must be one of low / medium / high."""
    await assert_pass(
        runnable=run_extractor,
        eval_inputs=_STRUCTURE_INPUTS,
        evaluators=[has_valid_priority],
    )


@pytest.mark.asyncio
async def test_summary_is_non_empty():
    """summary must be a non-empty string."""
    await assert_pass(
        runnable=run_extractor,
        eval_inputs=_STRUCTURE_INPUTS,
        evaluators=[has_non_empty_summary],
    )


# ---------------------------------------------------------------------------
# Test: all structure checks together with a lenient pass threshold (80 %)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_structure_pass_threshold():
    """All four structure checks must pass on at least 80 % of inputs."""
    await assert_pass(
        runnable=run_extractor,
        eval_inputs=_STRUCTURE_INPUTS,
        evaluators=[
            has_required_keys,
            has_valid_category,
            has_valid_priority,
            has_non_empty_summary,
        ],
        pass_criteria=ScoreThreshold(threshold=1.0, pct=0.8),
    )


# ---------------------------------------------------------------------------
# Test: golden dataset — category and priority must match expected outputs
# Run `python build_dataset.py` before this test.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dataset_category_and_priority():
    """Predicted category and priority must match the golden dataset."""
    await assert_dataset_pass(
        runnable=run_extractor,
        dataset_name="email-classifier-golden",
        evaluators=[
            category_matches_expected,
            priority_matches_expected,
        ],
        pass_criteria=ScoreThreshold(threshold=1.0, pct=0.8),
    )
