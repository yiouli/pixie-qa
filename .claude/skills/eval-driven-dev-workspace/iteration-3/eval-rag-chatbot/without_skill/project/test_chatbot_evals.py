"""Eval tests for the RAG chatbot using pixie.

These tests verify the chatbot's answer_question() function by:
1. Running it against a stored dataset (assert_dataset_pass).
2. Running individual questions and evaluating with ExactMatchEval.
3. Running with a custom evaluator that checks answer quality.

Run with:
    PYTHONPATH=/home/yiouli/repo/pixie-qa python -m pytest test_chatbot_evals.py -v
or with the pixie CLI:
    PYTHONPATH=/home/yiouli/repo/pixie-qa pixie test test_chatbot_evals.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

# Resolve paths
PROJECT_DIR = Path(__file__).parent
DATASET_DIR = PROJECT_DIR / "pixie_datasets"

# Set dataset dir env var before importing pixie so get_config() picks it up
os.environ.setdefault("PIXIE_DATASET_DIR", str(DATASET_DIR))

# Make sure the project is on sys.path
sys.path.insert(0, str(PROJECT_DIR))

import pixie.instrumentation as px
import pixie.instrumentation.observation as _px_obs
from pixie.evals.eval_utils import assert_dataset_pass, assert_pass, run_and_evaluate
from pixie.evals.evaluation import Evaluation
from pixie.evals.scorers import ExactMatchEval
from pixie.storage.evaluable import Evaluable
from pixie.storage.tree import ObservationNode

from chatbot import answer_question


# ---------------------------------------------------------------------------
# Helpers / custom evaluators
# ---------------------------------------------------------------------------


async def exact_match_evaluator(
    evaluable: Evaluable,
    *,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
    """Return score=1.0 when output matches expected, 0.0 otherwise."""
    output = str(evaluable.eval_output or "")
    expected = str(evaluable.expected_output or "")
    if output == expected:
        return Evaluation(score=1.0, reasoning=f"Exact match: {output!r}")
    return Evaluation(
        score=0.0,
        reasoning=f"Mismatch: got {output!r}, expected {expected!r}",
    )


async def non_empty_evaluator(
    evaluable: Evaluable,
    *,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
    """Return score=1.0 when output is a non-empty string."""
    output = evaluable.eval_output
    if output and str(output).strip():
        return Evaluation(score=1.0, reasoning="Answer is non-empty")
    return Evaluation(score=0.0, reasoning="Answer is empty or None")


async def contains_keyword_evaluator(
    evaluable: Evaluable,
    *,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
    """Return score=1.0 when the output contains the key geographic entity from the input."""
    question = str(evaluable.eval_input or "").lower()
    answer = str(evaluable.eval_output or "").lower()

    keyword_map = {
        "france": "france",
        "germany": "germany",
        "capital": "capital",
        "language": "german",
        "population": "million",
        "currency": "euro",
    }
    for q_kw, a_kw in keyword_map.items():
        if q_kw in question:
            if a_kw in answer:
                return Evaluation(
                    score=1.0,
                    reasoning=f"Answer contains expected keyword '{a_kw}'",
                )
            return Evaluation(
                score=0.0,
                reasoning=f"Answer missing expected keyword '{a_kw}' for question about '{q_kw}'",
            )
    return Evaluation(score=0.5, reasoning="Could not determine expected keyword")


# ---------------------------------------------------------------------------
# Tests — individual questions via run_and_evaluate
# ---------------------------------------------------------------------------


def test_capital_of_france():
    """answer_question returns Paris for capital-of-France query."""
    result = asyncio.run(
        run_and_evaluate(
            evaluator=exact_match_evaluator,
            runnable=answer_question,
            eval_input="What is the capital of France?",
            expected_output="Paris is the capital of France.",
        )
    )
    assert result.score == 1.0, f"Expected score=1.0, got {result.score}. Reasoning: {result.reasoning}"


def test_language_of_germany():
    """answer_question returns German-language info for Germany language query."""
    result = asyncio.run(
        run_and_evaluate(
            evaluator=exact_match_evaluator,
            runnable=answer_question,
            eval_input="What language do people speak in Germany?",
            expected_output="German is spoken in Germany and Austria.",
        )
    )
    assert result.score == 1.0, f"Expected score=1.0, got {result.score}. Reasoning: {result.reasoning}"


def test_population_of_france():
    """answer_question returns population info for France population query."""
    result = asyncio.run(
        run_and_evaluate(
            evaluator=exact_match_evaluator,
            runnable=answer_question,
            eval_input="What is the population of France?",
            expected_output="France has a population of about 68 million.",
        )
    )
    assert result.score == 1.0, f"Expected score=1.0, got {result.score}. Reasoning: {result.reasoning}"


def test_currency_of_germany():
    """answer_question returns Euro info for Germany currency query."""
    result = asyncio.run(
        run_and_evaluate(
            evaluator=exact_match_evaluator,
            runnable=answer_question,
            eval_input="What currency does Germany use?",
            expected_output="Germany also uses the Euro (EUR).",
        )
    )
    assert result.score == 1.0, f"Expected score=1.0, got {result.score}. Reasoning: {result.reasoning}"


def test_unknown_topic_returns_non_empty():
    """answer_question returns a non-empty string for an unknown query."""
    result = asyncio.run(
        run_and_evaluate(
            evaluator=non_empty_evaluator,
            runnable=answer_question,
            eval_input="What is the weather like in Paris?",
        )
    )
    assert result.score == 1.0, f"Expected score=1.0, got {result.score}. Reasoning: {result.reasoning}"


# ---------------------------------------------------------------------------
# Tests — assert_pass with multiple questions
# ---------------------------------------------------------------------------


def test_all_questions_non_empty():
    """All standard questions produce non-empty answers."""
    questions = [
        "What is the capital of France?",
        "What language do people speak in Germany?",
        "What is the population of France?",
        "What currency does Germany use?",
    ]
    asyncio.run(
        assert_pass(
            runnable=answer_question,
            eval_inputs=questions,
            evaluators=[non_empty_evaluator],
        )
    )


def test_all_questions_contain_keywords():
    """All standard questions produce answers containing the expected keywords."""
    questions = [
        "What is the capital of France?",
        "What language do people speak in Germany?",
        "What is the population of France?",
        "What currency does Germany use?",
    ]
    asyncio.run(
        assert_pass(
            runnable=answer_question,
            eval_inputs=questions,
            evaluators=[contains_keyword_evaluator],
        )
    )


def test_assert_pass_with_expected_outputs():
    """assert_pass with Evaluable items that carry expected_output."""
    evaluables = [
        Evaluable(
            eval_input="What is the capital of France?",
            expected_output="Paris is the capital of France.",
        ),
        Evaluable(
            eval_input="What language do people speak in Germany?",
            expected_output="German is spoken in Germany and Austria.",
        ),
        Evaluable(
            eval_input="What is the population of France?",
            expected_output="France has a population of about 68 million.",
        ),
        Evaluable(
            eval_input="What currency does Germany use?",
            expected_output="Germany also uses the Euro (EUR).",
        ),
    ]
    asyncio.run(
        assert_pass(
            runnable=answer_question,
            eval_inputs=[e.eval_input for e in evaluables],
            evaluators=[exact_match_evaluator],
            evaluables=evaluables,
        )
    )


# ---------------------------------------------------------------------------
# Tests — assert_dataset_pass (loads from saved dataset)
# ---------------------------------------------------------------------------


def test_dataset_pass():
    """Load the saved dataset and assert all answers pass exact match."""
    dataset_dir = str(DATASET_DIR)
    asyncio.run(
        assert_dataset_pass(
            runnable=answer_question,
            dataset_name="rag-chatbot-traces",
            evaluators=[exact_match_evaluator],
            dataset_dir=dataset_dir,
        )
    )


def test_dataset_keyword_coverage():
    """Load the saved dataset and assert keyword coverage for all answers."""
    dataset_dir = str(DATASET_DIR)
    asyncio.run(
        assert_dataset_pass(
            runnable=answer_question,
            dataset_name="rag-chatbot-traces",
            evaluators=[contains_keyword_evaluator],
            dataset_dir=dataset_dir,
        )
    )
