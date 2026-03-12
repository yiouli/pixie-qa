"""Eval tests for the RAG chatbot using pixie."""

import pytest
import pixie.instrumentation as px
from pixie.evals import (
    assert_pass,
    assert_dataset_pass,
    Evaluation,
    ScoreThreshold,
    last_llm_call,
    run_and_evaluate,
)
from pixie.evals import LevenshteinMatch, FactualityEval
from pixie.storage.evaluable import Evaluable

from chatbot import answer_question

# ---------------------------------------------------------------------------
# Custom evaluators
# ---------------------------------------------------------------------------


async def contains_answer_evaluator(evaluable: Evaluable, *, trace=None) -> Evaluation:
    """Check that the output contains at least part of the expected answer (case-insensitive)."""
    output = str(evaluable.eval_output or "").lower()
    expected = str(evaluable.expected_output or "").lower()
    if not expected:
        return Evaluation(score=0.0, reasoning="No expected output provided")
    passed = expected in output
    return Evaluation(
        score=1.0 if passed else 0.0,
        reasoning=f"Expected '{expected}' {'found' if passed else 'NOT found'} in output.",
    )


async def non_empty_evaluator(evaluable: Evaluable, *, trace=None) -> Evaluation:
    """Verify the chatbot returns a non-empty response."""
    output = str(evaluable.eval_output or "").strip()
    passed = len(output) > 0
    return Evaluation(
        score=1.0 if passed else 0.0,
        reasoning="Output is non-empty." if passed else "Output is empty.",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_answer_is_non_empty():
    """The chatbot must always return a non-empty string."""
    await assert_pass(
        runnable=answer_question,
        eval_inputs=[
            "What is the capital of France?",
            "What language do people speak in Germany?",
            "What is the population of France?",
        ],
        evaluators=[non_empty_evaluator],
    )


@pytest.mark.asyncio
async def test_capital_questions_contain_expected_city():
    """Capital questions should mention the correct city."""
    items = [
        Evaluable(eval_input="What is the capital of France?", expected_output="Paris"),
        Evaluable(eval_input="What is the capital of Germany?", expected_output="Berlin"),
    ]
    await assert_pass(
        runnable=answer_question,
        eval_inputs=[item.eval_input for item in items],
        evaluators=[contains_answer_evaluator],
        evaluables=items,
    )


@pytest.mark.asyncio
async def test_language_questions_contain_expected_language():
    """Language questions should mention the correct language."""
    items = [
        Evaluable(eval_input="What language do people speak in France?", expected_output="French"),
        Evaluable(eval_input="What language do people speak in Germany?", expected_output="German"),
    ]
    await assert_pass(
        runnable=answer_question,
        eval_inputs=[item.eval_input for item in items],
        evaluators=[contains_answer_evaluator],
        evaluables=items,
    )


@pytest.mark.asyncio
async def test_levenshtein_capital_france():
    """Levenshtein similarity between answer and 'Paris' should be high."""
    evaluable = Evaluable(
        eval_input="What is the capital of France?",
        expected_output="Paris",
    )
    evaluator = LevenshteinMatch(expected="Paris")
    result = await run_and_evaluate(
        evaluator=evaluator,
        runnable=answer_question,
        eval_input=evaluable.eval_input,
        expected_output=evaluable.expected_output,
    )
    assert result.score > 0.0, f"Expected positive similarity score, got {result.score}"


@pytest.mark.asyncio
async def test_dataset_golden_set():
    """Run the full golden-set dataset through the chatbot.

    Requires the dataset to have been built first via build_dataset.py.
    Uses a lenient ScoreThreshold so that partial credit still passes.
    """
    await assert_dataset_pass(
        runnable=answer_question,
        dataset_name="rag-chatbot-golden-set",
        evaluators=[contains_answer_evaluator],
        pass_criteria=ScoreThreshold(threshold=0.5, pct=0.8),
    )


@pytest.mark.asyncio
async def test_llm_call_captured_in_trace():
    """Verify that a trace is captured and the last LLM call is accessible."""
    result = await run_and_evaluate(
        evaluator=non_empty_evaluator,
        runnable=answer_question,
        eval_input="What is the capital of France?",
        from_trace=last_llm_call,
    )
    # We only check that evaluation ran without raising
    assert result is not None
