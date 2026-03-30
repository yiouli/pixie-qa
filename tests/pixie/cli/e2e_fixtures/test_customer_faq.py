"""Eval tests for customer service FAQ quality.

These tests verify that the customer service chatbot produces
accurate, complete, and appropriate answers to common questions.
They use the ``customer-faq`` golden dataset and multiple evaluators
with different scoring strategies.

NOTE: This test file is used for e2e testing of ``pixie test``.
It uses mock evaluators (no LLM API calls) for determinism.
"""

from pathlib import Path

from pixie import ScoreThreshold, assert_dataset_pass
from tests.pixie.cli.e2e_fixtures.mock_evaluators import (
    MockClosedQAEval,
    MockFactualityEval,
    MockFailingEval,
    MockHallucinationEval,
)

# ── Dataset directory override ───────────────────────────────────────
# Point at the fixtures/datasets/ dir so assert_dataset_pass finds
# the golden dataset JSON.
_DATASET_DIR = str(Path(__file__).resolve().parent / "datasets")


async def _noop_runnable(eval_input: object) -> None:
    """No-op runnable — dataset items already carry eval_output."""


# ── Test 1: Factuality across the full dataset ──────────────────────


async def test_faq_factuality() -> None:
    """FAQ answers are factually consistent with expected answers.

    Uses MockFactuality (string-similarity based) with a lenient
    threshold: 60% score required on 80% of items.
    """
    await assert_dataset_pass(
        runnable=_noop_runnable,
        dataset_name="customer-faq",
        evaluators=[MockFactualityEval()],
        dataset_dir=_DATASET_DIR,
        pass_criteria=ScoreThreshold(threshold=0.6, pct=0.8),
    )


# ── Test 2: Multiple evaluators (factuality + QA coverage) ──────────


async def test_faq_multi_evaluator() -> None:
    """FAQ answers pass both factuality and closed-QA checks.

    Runs two evaluators on every dataset item. Both must score >= 0.5
    on all items (strict — pct=1.0).
    """
    await assert_dataset_pass(
        runnable=_noop_runnable,
        dataset_name="customer-faq",
        evaluators=[MockFactualityEval(), MockClosedQAEval()],
        dataset_dir=_DATASET_DIR,
        pass_criteria=ScoreThreshold(threshold=0.5, pct=1.0),
    )


# ── Test 3: Hallucination check (should always pass) ────────────────


async def test_faq_no_hallucinations() -> None:
    """FAQ answers do not contain hallucinated information.

    Uses a lenient hallucination detector. All items must pass.
    """
    await assert_dataset_pass(
        runnable=_noop_runnable,
        dataset_name="customer-faq",
        evaluators=[MockHallucinationEval()],
        dataset_dir=_DATASET_DIR,
        pass_criteria=ScoreThreshold(threshold=0.5, pct=1.0),
    )


# ── Test 4: Strict tone check (expected to FAIL) ────────────────────


async def test_faq_tone_check() -> None:
    """FAQ answers match formal tone guidelines.

    This test is expected to FAIL because MockFailingEval always
    returns low scores. This exercises the failure path in
    ``pixie test`` reporting and scorecard generation.
    """
    await assert_dataset_pass(
        runnable=_noop_runnable,
        dataset_name="customer-faq",
        evaluators=[MockFailingEval()],
        dataset_dir=_DATASET_DIR,
        pass_criteria=ScoreThreshold(threshold=0.5, pct=1.0),
    )
