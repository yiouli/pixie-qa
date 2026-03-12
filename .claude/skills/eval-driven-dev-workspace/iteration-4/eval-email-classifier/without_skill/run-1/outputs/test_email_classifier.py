"""Eval-based tests for the email classifier using pixie.

These tests instrument extract_from_email, run it on sample inputs, and
evaluate the outputs using pixie evaluators.

Run with:
    PYTHONPATH=/home/yiouli/repo/pixie-qa pytest test_email_classifier.py -v

Or generate the dataset first:
    PYTHONPATH=/home/yiouli/repo/pixie-qa python generate_dataset.py
Then run:
    PYTHONPATH=/home/yiouli/repo/pixie-qa pytest test_email_classifier.py -v
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

import pytest

# Ensure project dir is importable
sys.path.insert(0, os.path.dirname(__file__))

import pixie.instrumentation.observation as _px_obs
from pixie.evals.evaluation import Evaluation
from pixie.evals.eval_utils import assert_pass, assert_dataset_pass, EvalAssertionError
from pixie.evals.trace_capture import capture_traces
from pixie.storage.evaluable import Evaluable, as_evaluable
from pixie.storage.tree import build_tree, ObservationNode

from instrumented_extractor import extract_from_email

# ---------------------------------------------------------------------------
# Project-local dataset directory
# ---------------------------------------------------------------------------

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(PROJECT_DIR, "pixie_datasets")
DATASET_NAME = "email-classifier-traces"

# ---------------------------------------------------------------------------
# Sample inputs used in live-capture tests
# ---------------------------------------------------------------------------

SAMPLE_EMAILS = [
    "Hi, my subscription was charged twice this month. Please refund the duplicate charge ASAP.",
    "The app keeps crashing when I try to upload files larger than 10MB. This is urgent.",
    "Can you tell me how to reset my password? I can't find the option in settings.",
    "Just wondering when your mobile app will support dark mode.",
    "I received an invoice for an amount I don't recognize. Please help clarify this billing issue.",
]

# ---------------------------------------------------------------------------
# Custom evaluators
# ---------------------------------------------------------------------------

VALID_CATEGORIES = {"billing", "technical", "account", "general"}
VALID_PRIORITIES = {"low", "medium", "high"}


async def has_required_keys(
    evaluable: Evaluable,
    *,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
    """Check that eval_output is a dict with 'category', 'priority', and 'summary'."""
    output = evaluable.eval_output
    if not isinstance(output, dict):
        # eval_output is serialised via jsonpickle — could be a JSON string
        if isinstance(output, str):
            try:
                output = json.loads(output)
            except (json.JSONDecodeError, TypeError):
                return Evaluation(
                    score=0.0,
                    reasoning=f"Output is a non-JSON string: {output!r}",
                )
        else:
            return Evaluation(
                score=0.0,
                reasoning=f"Expected dict output, got {type(output).__name__}: {output!r}",
            )

    required = {"category", "priority", "summary"}
    missing = required - set(output.keys())
    if missing:
        return Evaluation(
            score=0.0,
            reasoning=f"Output missing required keys: {sorted(missing)}",
        )
    return Evaluation(
        score=1.0,
        reasoning="Output contains all required keys: category, priority, summary.",
    )


async def valid_category(
    evaluable: Evaluable,
    *,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
    """Check that 'category' is one of the allowed values."""
    output = evaluable.eval_output
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            pass
    if not isinstance(output, dict):
        return Evaluation(score=0.0, reasoning="Output is not a dict.")
    cat = output.get("category")
    if cat in VALID_CATEGORIES:
        return Evaluation(
            score=1.0,
            reasoning=f"category={cat!r} is valid.",
        )
    return Evaluation(
        score=0.0,
        reasoning=f"category={cat!r} is not in {VALID_CATEGORIES}.",
    )


async def valid_priority(
    evaluable: Evaluable,
    *,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
    """Check that 'priority' is one of the allowed values."""
    output = evaluable.eval_output
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            pass
    if not isinstance(output, dict):
        return Evaluation(score=0.0, reasoning="Output is not a dict.")
    pri = output.get("priority")
    if pri in VALID_PRIORITIES:
        return Evaluation(
            score=1.0,
            reasoning=f"priority={pri!r} is valid.",
        )
    return Evaluation(
        score=0.0,
        reasoning=f"priority={pri!r} is not in {VALID_PRIORITIES}.",
    )


async def non_empty_summary(
    evaluable: Evaluable,
    *,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
    """Check that 'summary' is a non-empty string."""
    output = evaluable.eval_output
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            pass
    if not isinstance(output, dict):
        return Evaluation(score=0.0, reasoning="Output is not a dict.")
    summary = output.get("summary")
    if isinstance(summary, str) and len(summary.strip()) > 0:
        return Evaluation(
            score=1.0,
            reasoning=f"summary is a non-empty string ({len(summary)} chars).",
        )
    return Evaluation(
        score=0.0,
        reasoning=f"summary is empty or not a string: {summary!r}",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_instrumentation():
    """Reset pixie instrumentation state before each test to avoid cross-test bleed."""
    _px_obs._reset_state()
    yield
    _px_obs._reset_state()


# ---------------------------------------------------------------------------
# Tests: live capture (no pre-saved dataset required)
# ---------------------------------------------------------------------------


class TestLiveCapture:
    """Run the extractor on sample inputs, capture traces, and evaluate."""

    def test_spans_are_captured(self):
        """Instrumented function should produce at least one span per call."""
        with capture_traces() as handler:
            extract_from_email("My payment failed. Please help!")
        assert len(handler.spans) >= 1, "Expected at least one span to be captured."

    def test_span_has_input_and_output(self):
        """Captured span should carry the email text as input and a dict as output."""
        email = "I need to reset my password urgently."
        with capture_traces() as handler:
            extract_from_email(email)

        assert handler.spans, "No spans captured."
        span = handler.spans[0]

        # eval_input should contain the email text somewhere
        ev = as_evaluable(span)
        assert ev.eval_input is not None, "eval_input should not be None."
        assert ev.eval_output is not None, "eval_output should not be None."

    async def test_all_emails_pass_structure_checks(self):
        """All sample emails should produce structurally valid JSON output."""
        evaluators = [has_required_keys, valid_category, valid_priority, non_empty_summary]
        await assert_pass(
            runnable=extract_from_email,
            eval_inputs=SAMPLE_EMAILS,
            evaluators=evaluators,
        )

    async def test_billing_email_categorised_as_billing(self):
        """A billing email should be categorised as 'billing'."""
        email = "I was charged twice. Please refund the duplicate charge."
        with capture_traces() as handler:
            result = extract_from_email(email)

        assert result["category"] == "billing", (
            f"Expected 'billing' category, got {result['category']!r}"
        )

    async def test_technical_email_categorised_as_technical(self):
        """A technical email should be categorised as 'technical'."""
        email = "The app keeps crashing when I try to upload a file."
        with capture_traces() as handler:
            result = extract_from_email(email)

        assert result["category"] == "technical", (
            f"Expected 'technical' category, got {result['category']!r}"
        )

    async def test_urgent_email_has_high_priority(self):
        """An urgent email should receive 'high' priority."""
        email = "This is URGENT — my account was hacked and I need help immediately!"
        with capture_traces() as handler:
            result = extract_from_email(email)

        assert result["priority"] == "high", (
            f"Expected 'high' priority, got {result['priority']!r}"
        )

    async def test_account_reset_email(self):
        """A password-reset email should be categorised as 'account'."""
        email = "I forgot my password and need to reset it."
        with capture_traces() as handler:
            result = extract_from_email(email)

        assert result["category"] == "account", (
            f"Expected 'account' category, got {result['category']!r}"
        )


# ---------------------------------------------------------------------------
# Tests: dataset-backed (requires generate_dataset.py to have been run first)
# ---------------------------------------------------------------------------


class TestDatasetBacked:
    """Load the pre-saved dataset and evaluate every item."""

    @pytest.fixture(autouse=True)
    def _check_dataset_exists(self):
        """Skip all dataset tests if the dataset file hasn't been generated yet."""
        dataset_file = os.path.join(DATASET_DIR, "email-classifier-traces.json")
        if not os.path.isfile(dataset_file):
            pytest.skip(
                "Dataset not found. Run 'python generate_dataset.py' first to generate it."
            )

    async def test_dataset_all_required_keys(self):
        """Every item in the saved dataset should have category, priority, summary."""
        await assert_dataset_pass(
            runnable=extract_from_email,
            dataset_name=DATASET_NAME,
            evaluators=[has_required_keys],
            dataset_dir=DATASET_DIR,
        )

    async def test_dataset_valid_category(self):
        """Every item in the saved dataset should have a valid category."""
        await assert_dataset_pass(
            runnable=extract_from_email,
            dataset_name=DATASET_NAME,
            evaluators=[valid_category],
            dataset_dir=DATASET_DIR,
        )

    async def test_dataset_valid_priority(self):
        """Every item in the saved dataset should have a valid priority."""
        await assert_dataset_pass(
            runnable=extract_from_email,
            dataset_name=DATASET_NAME,
            evaluators=[valid_priority],
            dataset_dir=DATASET_DIR,
        )

    async def test_dataset_non_empty_summary(self):
        """Every item in the saved dataset should have a non-empty summary."""
        await assert_dataset_pass(
            runnable=extract_from_email,
            dataset_name=DATASET_NAME,
            evaluators=[non_empty_summary],
            dataset_dir=DATASET_DIR,
        )

    async def test_dataset_all_checks_combined(self):
        """Combined: run all four structural checks against the entire dataset."""
        await assert_dataset_pass(
            runnable=extract_from_email,
            dataset_name=DATASET_NAME,
            evaluators=[has_required_keys, valid_category, valid_priority, non_empty_summary],
            dataset_dir=DATASET_DIR,
        )
