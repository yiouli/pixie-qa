"""Eval test suite for the email classifier.

Run with:

    PYTHONPATH=/home/yiouli/repo/pixie-qa python -m pytest test_email_classifier.py -v

Or using the pixie test runner (if installed):

    PYTHONPATH=/home/yiouli/repo/pixie-qa pixie test test_email_classifier.py

Prerequisites:
    1. Run `python build_dataset.py` once to create the golden dataset.
    2. The instrumented extractor.py must be in the same directory.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from pixie.evals.eval_utils import assert_dataset_pass, assert_pass
from pixie.evals.evaluation import Evaluation
from pixie.storage.evaluable import Evaluable
from pixie.storage.tree import ObservationNode

from extractor import extract_from_email

DATASET_NAME = "email-classifier-golden"
DATASET_DIR = str(Path(__file__).parent / "datasets")


# ---------------------------------------------------------------------------
# Evaluators
# ---------------------------------------------------------------------------


def _parse_output(output: Any) -> dict:
    """Parse the classifier output from an Evaluable.

    The @observe decorator serialises the return value via jsonpickle.
    We accept both a dict and a JSON string.
    """
    if isinstance(output, dict):
        return output
    if isinstance(output, str):
        return json.loads(output)
    raise ValueError(f"Unexpected output type: {type(output)!r}")


def _parse_expected(expected: Any) -> dict:
    """Parse the expected output from an Evaluable."""
    if isinstance(expected, dict):
        return expected
    if isinstance(expected, str):
        return json.loads(expected)
    raise ValueError(f"Unexpected expected_output type: {type(expected)!r}")


async def category_matches(
    evaluable: Evaluable,
    *,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
    """Check that the predicted category exactly matches the expected category."""
    try:
        actual = _parse_output(evaluable.eval_output)
        expected = _parse_expected(evaluable.expected_output)

        predicted_category = actual.get("category")
        expected_category = expected.get("category")

        if predicted_category == expected_category:
            return Evaluation(
                score=1.0,
                reasoning=f"Category correct: '{predicted_category}'",
                details={"predicted": predicted_category, "expected": expected_category},
            )
        return Evaluation(
            score=0.0,
            reasoning=f"Category mismatch: got '{predicted_category}', expected '{expected_category}'",
            details={"predicted": predicted_category, "expected": expected_category},
        )
    except Exception as exc:
        return Evaluation(
            score=0.0,
            reasoning=f"Evaluator error: {exc}",
            details={"error": str(exc)},
        )


async def priority_matches(
    evaluable: Evaluable,
    *,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
    """Check that the predicted priority exactly matches the expected priority."""
    try:
        actual = _parse_output(evaluable.eval_output)
        expected = _parse_expected(evaluable.expected_output)

        predicted_priority = actual.get("priority")
        expected_priority = expected.get("priority")

        if predicted_priority == expected_priority:
            return Evaluation(
                score=1.0,
                reasoning=f"Priority correct: '{predicted_priority}'",
                details={"predicted": predicted_priority, "expected": expected_priority},
            )
        return Evaluation(
            score=0.0,
            reasoning=f"Priority mismatch: got '{predicted_priority}', expected '{expected_priority}'",
            details={"predicted": predicted_priority, "expected": expected_priority},
        )
    except Exception as exc:
        return Evaluation(
            score=0.0,
            reasoning=f"Evaluator error: {exc}",
            details={"error": str(exc)},
        )


async def summary_is_non_empty(
    evaluable: Evaluable,
    *,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
    """Check that the summary field is a non-empty string."""
    try:
        actual = _parse_output(evaluable.eval_output)
        summary = actual.get("summary", "")

        if isinstance(summary, str) and summary.strip():
            return Evaluation(
                score=1.0,
                reasoning=f"Summary is non-empty: '{summary[:60]}...'",
                details={"summary": summary},
            )
        return Evaluation(
            score=0.0,
            reasoning="Summary is missing or empty",
            details={"summary": summary},
        )
    except Exception as exc:
        return Evaluation(
            score=0.0,
            reasoning=f"Evaluator error: {exc}",
            details={"error": str(exc)},
        )


async def output_has_required_fields(
    evaluable: Evaluable,
    *,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
    """Check that the output contains all three required fields: category, priority, summary."""
    required = {"category", "priority", "summary"}
    try:
        actual = _parse_output(evaluable.eval_output)
        missing = required - set(actual.keys())

        if not missing:
            return Evaluation(
                score=1.0,
                reasoning="All required fields present: category, priority, summary",
                details={"fields": list(actual.keys())},
            )
        return Evaluation(
            score=0.0,
            reasoning=f"Missing required fields: {sorted(missing)}",
            details={"missing": sorted(missing), "present": sorted(actual.keys())},
        )
    except Exception as exc:
        return Evaluation(
            score=0.0,
            reasoning=f"Evaluator error: {exc}",
            details={"error": str(exc)},
        )


async def category_is_valid(
    evaluable: Evaluable,
    *,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
    """Check that the category value is one of the allowed values."""
    allowed = {"billing", "technical", "account", "general"}
    try:
        actual = _parse_output(evaluable.eval_output)
        category = actual.get("category")

        if category in allowed:
            return Evaluation(
                score=1.0,
                reasoning=f"Category '{category}' is a valid value",
                details={"category": category, "allowed": sorted(allowed)},
            )
        return Evaluation(
            score=0.0,
            reasoning=f"Category '{category}' is not a valid value. Allowed: {sorted(allowed)}",
            details={"category": category, "allowed": sorted(allowed)},
        )
    except Exception as exc:
        return Evaluation(
            score=0.0,
            reasoning=f"Evaluator error: {exc}",
            details={"error": str(exc)},
        )


async def priority_is_valid(
    evaluable: Evaluable,
    *,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
    """Check that the priority value is one of the allowed values."""
    allowed = {"low", "medium", "high"}
    try:
        actual = _parse_output(evaluable.eval_output)
        priority = actual.get("priority")

        if priority in allowed:
            return Evaluation(
                score=1.0,
                reasoning=f"Priority '{priority}' is a valid value",
                details={"priority": priority, "allowed": sorted(allowed)},
            )
        return Evaluation(
            score=0.0,
            reasoning=f"Priority '{priority}' is not a valid value. Allowed: {sorted(allowed)}",
            details={"priority": priority, "allowed": sorted(allowed)},
        )
    except Exception as exc:
        return Evaluation(
            score=0.0,
            reasoning=f"Evaluator error: {exc}",
            details={"error": str(exc)},
        )


# ---------------------------------------------------------------------------
# Test functions (discovered by pixie test runner or pytest)
# ---------------------------------------------------------------------------


def test_output_schema() -> None:
    """All outputs must contain the three required fields with valid enum values."""
    asyncio.run(
        assert_dataset_pass(
            runnable=extract_from_email,
            dataset_name=DATASET_NAME,
            evaluators=[
                output_has_required_fields,
                category_is_valid,
                priority_is_valid,
                summary_is_non_empty,
            ],
            dataset_dir=DATASET_DIR,
        )
    )


def test_category_accuracy() -> None:
    """The classifier must correctly categorise every email in the golden dataset."""
    asyncio.run(
        assert_dataset_pass(
            runnable=extract_from_email,
            dataset_name=DATASET_NAME,
            evaluators=[category_matches],
            dataset_dir=DATASET_DIR,
        )
    )


def test_priority_accuracy() -> None:
    """The classifier must correctly determine the priority of every email."""
    asyncio.run(
        assert_dataset_pass(
            runnable=extract_from_email,
            dataset_name=DATASET_NAME,
            evaluators=[priority_matches],
            dataset_dir=DATASET_DIR,
        )
    )


def test_full_pipeline() -> None:
    """End-to-end check: schema validity, correct category, correct priority, and non-empty summary."""
    asyncio.run(
        assert_dataset_pass(
            runnable=extract_from_email,
            dataset_name=DATASET_NAME,
            evaluators=[
                output_has_required_fields,
                category_is_valid,
                priority_is_valid,
                summary_is_non_empty,
                category_matches,
                priority_matches,
            ],
            dataset_dir=DATASET_DIR,
        )
    )


# ---------------------------------------------------------------------------
# Inline smoke test — no dataset required
# ---------------------------------------------------------------------------


def test_billing_email_inline() -> None:
    """Quick inline test for a billing email without using the dataset."""
    email = "My subscription was charged twice. Refund the duplicate charge ASAP."
    asyncio.run(
        assert_pass(
            runnable=extract_from_email,
            eval_inputs=[email],
            evaluators=[
                output_has_required_fields,
                category_is_valid,
                priority_is_valid,
                summary_is_non_empty,
            ],
        )
    )


def test_technical_email_inline() -> None:
    """Quick inline test for a technical email without using the dataset."""
    email = "The app crashes whenever I try to upload files. This is urgent."
    asyncio.run(
        assert_pass(
            runnable=extract_from_email,
            eval_inputs=[email],
            evaluators=[
                output_has_required_fields,
                category_is_valid,
                priority_is_valid,
                summary_is_non_empty,
            ],
        )
    )
