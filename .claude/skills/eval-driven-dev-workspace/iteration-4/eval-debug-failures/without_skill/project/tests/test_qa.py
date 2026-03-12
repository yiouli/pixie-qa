"""Eval-based tests for the Q&A app — currently failing."""

import asyncio
from pixie import enable_storage
from pixie.evals import assert_dataset_pass, FactualityEval, ScoreThreshold

from qa_app import answer_question


def runnable(eval_input):
    enable_storage()
    question = eval_input.get("question", "") if isinstance(eval_input, dict) else str(eval_input)
    context = eval_input.get("context", "") if isinstance(eval_input, dict) else ""
    return answer_question(question=question, context=context)


async def test_factuality():
    """Test that answers are factually accurate compared to expected outputs."""
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name="qa-golden-set",
        evaluators=[FactualityEval()],
        pass_criteria=ScoreThreshold(threshold=0.7, pct=0.8),
    )
