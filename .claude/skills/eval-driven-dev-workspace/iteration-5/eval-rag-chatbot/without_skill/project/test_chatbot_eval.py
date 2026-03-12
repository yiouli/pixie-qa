"""Eval tests for the RAG chatbot.

Uses pixie's eval harness to run the golden dataset against answer_question()
and check that answers are correct using ExactMatchEval.

Run with:
    PYTHONPATH=/home/yiouli/repo/pixie-qa pytest test_chatbot_eval.py -v
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import pixie.instrumentation.observation as _px_obs
from pixie.dataset.store import DatasetStore
from pixie.evals.eval_utils import assert_dataset_pass, assert_pass
from pixie.evals.scorers import ExactMatchEval, LevenshteinMatch
from pixie.storage.evaluable import Evaluable

# Project directory — dataset lives alongside this file.
_PROJECT_DIR = Path(__file__).parent
_DATASET_DIR = _PROJECT_DIR / "datasets"
_DATASET_NAME = "rag-chatbot-golden"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_instrumentation():
    """Reset global instrumentation state between tests to avoid cross-test pollution."""
    _px_obs._reset_state()
    yield
    _px_obs._reset_state()


# ---------------------------------------------------------------------------
# Runnable wrapper
# ---------------------------------------------------------------------------

def run_chatbot(question: str) -> None:
    """Thin wrapper that runs answer_question() inside a pixie observation span.

    assert_pass / run_and_evaluate expect a runnable that:
      - accepts a single eval_input value
      - produces at least one ObserveSpan via pixie instrumentation

    The @observe decorator on answer_question() handles span creation
    automatically, so we just call it here.
    """
    # Import here so instrumentation is already initialised before import-time
    # module-level px.init() runs inside chatbot.py.
    from chatbot import answer_question  # noqa: PLC0415

    answer_question(question)


# ---------------------------------------------------------------------------
# Exact-match eval against the golden dataset
# ---------------------------------------------------------------------------


class TestChatbotEvalDataset:
    """Eval tests that load the golden dataset from disk."""

    @pytest.mark.asyncio
    async def test_exact_match_golden_dataset(self):
        """Every answer in the golden dataset must exactly match expected output."""
        await assert_dataset_pass(
            runnable=run_chatbot,
            dataset_name=_DATASET_NAME,
            evaluators=[ExactMatchEval()],
            dataset_dir=str(_DATASET_DIR),
        )

    @pytest.mark.asyncio
    async def test_levenshtein_similarity_golden_dataset(self):
        """Every answer must score >= 0.8 on Levenshtein string similarity."""
        from pixie.evals.criteria import ScoreThreshold  # noqa: PLC0415

        await assert_dataset_pass(
            runnable=run_chatbot,
            dataset_name=_DATASET_NAME,
            evaluators=[LevenshteinMatch()],
            dataset_dir=str(_DATASET_DIR),
            pass_criteria=ScoreThreshold(threshold=0.8),
        )


# ---------------------------------------------------------------------------
# Inline eval — no dataset file required
# ---------------------------------------------------------------------------


class TestChatbotEvalInline:
    """Eval tests using inline Evaluable items (no dataset file needed)."""

    # Golden pairs: (question, expected_answer)
    _GOLDEN = [
        ("What is the capital of France?", "Paris is the capital of France."),
        ("What language do people speak in Germany?", "German is spoken in Germany and Austria."),
        ("What is the population of France?", "France has a population of about 68 million."),
        ("What currency does Germany use?", "Germany also uses the Euro (EUR)."),
        ("What is the capital of Germany?", "Berlin is the capital of Germany."),
        ("What currency does France use?", "France uses the Euro (EUR)."),
    ]

    @pytest.mark.asyncio
    async def test_exact_match_inline(self):
        """Inline exact-match eval — no dataset file required."""
        eval_inputs = [q for q, _ in self._GOLDEN]
        evaluables = [
            Evaluable(eval_input=q, expected_output=expected)
            for q, expected in self._GOLDEN
        ]

        await assert_pass(
            runnable=run_chatbot,
            eval_inputs=eval_inputs,
            evaluators=[ExactMatchEval()],
            evaluables=evaluables,
        )

    @pytest.mark.asyncio
    async def test_unknown_question_returns_fallback(self):
        """Questions with no matching keyword return a 'No relevant documents' answer."""
        from pixie.evals.eval_utils import run_and_evaluate  # noqa: PLC0415
        from pixie.evals.evaluation import Evaluation  # noqa: PLC0415
        from pixie.storage.evaluable import Evaluable as _Evaluable  # noqa: PLC0415
        from pixie.storage.tree import ObservationNode  # noqa: PLC0415

        async def check_fallback(
            evaluable: _Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            output = evaluable.eval_output or ""
            assert "No relevant documents" in str(output), (
                f"Expected fallback message, got: {output!r}"
            )
            return Evaluation(score=1.0, reasoning="fallback present")

        result = await run_and_evaluate(
            evaluator=check_fallback,
            runnable=run_chatbot,
            eval_input="What is the weather in Paris?",
        )
        assert result.score == 1.0
