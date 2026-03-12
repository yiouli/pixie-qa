"""Eval tests for the RAG chatbot.

Run with:
    pixie-test tests/
    pixie-test tests/ -v
    pixie-test -k factuality -v
"""

from pixie import enable_storage
from pixie.evals import (
    assert_dataset_pass,
    FactualityEval,
    AnswerRelevancyEval,
    ScoreThreshold,
    root,
)

import sys
import os

# Ensure the project root is on the path so chatbot can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chatbot import answer_question


def runnable(eval_input):
    """Replay one dataset item through the chatbot. enable_storage() ensures the trace is captured."""
    enable_storage()
    if isinstance(eval_input, dict):
        answer_question(**eval_input)
    else:
        answer_question(eval_input)


async def test_factuality():
    """Answers must be factually correct relative to the expected output."""
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name="rag-chatbot-golden",
        evaluators=[FactualityEval()],
        pass_criteria=ScoreThreshold(threshold=0.7, pct=0.8),
        from_trace=root,
    )


async def test_answer_relevancy():
    """Answers must be relevant to the question asked."""
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name="rag-chatbot-golden",
        evaluators=[AnswerRelevancyEval()],
        pass_criteria=ScoreThreshold(threshold=0.7, pct=0.8),
        from_trace=root,
    )
