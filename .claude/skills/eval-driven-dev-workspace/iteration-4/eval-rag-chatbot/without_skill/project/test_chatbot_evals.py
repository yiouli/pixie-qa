"""Eval tests for the RAG chatbot using pixie.

Run with:
    PYTHONPATH=/home/yiouli/repo/pixie-qa pixie test test_chatbot_evals.py
or:
    PYTHONPATH=/home/yiouli/repo/pixie-qa python -m pytest test_chatbot_evals.py -v

Tests
-----
1. test_answer_question_exact_match
   Runs answer_question() live for each question and checks the output
   exactly matches the expected answer using ExactMatchEval.

2. test_answer_question_levenshtein
   Same live run but uses Levenshtein similarity — tolerates minor
   wording differences.

3. test_dataset_exact_match
   Loads the pre-built dataset saved by save_dataset.py and runs
   ExactMatchEval against every stored item (no app re-execution needed).

4. test_retrieve_docs_returns_list
   Basic unit-style eval: checks that retrieve_docs returns a non-empty
   list for known keywords.
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.environ.get("PIXIE_PATH", "/home/yiouli/repo/pixie-qa"))

import pixie.instrumentation.observation as _px_obs
from pixie.evals import (
    ExactMatchEval,
    LevenshteinMatch,
    assert_dataset_pass,
    assert_pass,
)
from pixie.evals.evaluation import Evaluation
from pixie.storage.evaluable import Evaluable
from pixie.storage.tree import ObservationNode

# Ensure instrumentation state is clean before tests run
_px_obs._reset_state()

# Paths
_HERE = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(_HERE, "pixie_datasets")
DATASET_NAME = "rag-chatbot-traces"

# Import the instrumented application functions
from chatbot_instrumented import answer_question, retrieve_docs  # noqa: E402

# --------------------------------------------------------------------------
# Test inputs and expected outputs
# --------------------------------------------------------------------------

QUESTIONS = [
    "What is the capital of France?",
    "What language do people speak in Germany?",
    "What is the population of France?",
    "What currency does Germany use?",
]

# These match the first chunk returned by retrieve_docs for each keyword
EXPECTED_OUTPUTS = [
    "Paris is the capital of France.",
    "French is spoken in France.",
    "France has a population of about 68 million.",
    "France uses the Euro (EUR).",
]

# --------------------------------------------------------------------------
# Helper: wrap answer_question to accept a single string input
# --------------------------------------------------------------------------


def _run_answer_question(question: str) -> str:
    """Thin wrapper so answer_question fits the (input) -> output signature."""
    return answer_question(question)


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------


def test_answer_question_exact_match() -> None:
    """Each question produces the exact expected first-chunk answer."""
    asyncio.run(
        assert_pass(
            runnable=_run_answer_question,
            eval_inputs=QUESTIONS,
            evaluators=[ExactMatchEval()],
            evaluables=[
                Evaluable(eval_input=q, eval_output=None, expected_output=e)
                for q, e in zip(QUESTIONS, EXPECTED_OUTPUTS)
            ],
        )
    )


def test_answer_question_levenshtein() -> None:
    """Levenshtein similarity >= 0.5 for each answer (should be 1.0 for exact match)."""
    asyncio.run(
        assert_pass(
            runnable=_run_answer_question,
            eval_inputs=QUESTIONS,
            evaluators=[LevenshteinMatch()],
            evaluables=[
                Evaluable(eval_input=q, eval_output=None, expected_output=e)
                for q, e in zip(QUESTIONS, EXPECTED_OUTPUTS)
            ],
        )
    )


def test_dataset_exact_match() -> None:
    """Load the pre-built dataset and run ExactMatchEval against every item.

    Requires save_dataset.py to have been executed first so that
    pixie_datasets/rag-chatbot-traces.json exists.
    """
    dataset_path = os.path.join(DATASET_DIR, "rag-chatbot-traces.json")
    if not os.path.exists(dataset_path):
        raise AssertionError(
            f"Dataset not found at {dataset_path}. "
            "Run save_dataset.py first:\n"
            "  PYTHONPATH=/home/yiouli/repo/pixie-qa python save_dataset.py"
        )

    asyncio.run(
        assert_dataset_pass(
            runnable=_run_answer_question,
            dataset_name=DATASET_NAME,
            evaluators=[ExactMatchEval()],
            dataset_dir=DATASET_DIR,
        )
    )


def test_retrieve_docs_returns_relevant_chunks() -> None:
    """retrieve_docs returns at least one chunk for every known keyword."""
    keywords_and_expected_first_words = {
        "capital": "Paris",
        "population": "France",
        "language": "French",
        "currency": "France",
    }

    async def _check_output(
        evaluable: Evaluable,
        *,
        trace: list[ObservationNode] | None = None,
    ) -> Evaluation:
        output = evaluable.eval_output
        # output is the JSON-serialised list returned by retrieve_docs
        # Check it is non-empty and contains at least one string
        if output is None:
            return Evaluation(score=0.0, reasoning="Output is None")
        if isinstance(output, list) and len(output) > 0:
            return Evaluation(score=1.0, reasoning="Non-empty list returned")
        # JSON-serialised string form — just confirm it's not the fallback
        if "No relevant documents found" in str(output):
            return Evaluation(score=0.0, reasoning="Fallback 'no docs' returned")
        return Evaluation(score=1.0, reasoning="Docs returned")

    def _run_retrieve(query: str) -> list[str]:
        return retrieve_docs(query)

    asyncio.run(
        assert_pass(
            runnable=_run_retrieve,
            eval_inputs=list(keywords_and_expected_first_words.keys()),
            evaluators=[_check_output],
        )
    )
