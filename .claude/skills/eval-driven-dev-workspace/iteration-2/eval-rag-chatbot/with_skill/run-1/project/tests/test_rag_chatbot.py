"""
Eval tests for the RAG chatbot.

Prerequisites:
  1. Build the dataset:  python build_dataset.py
  2. Set ANTHROPIC_API_KEY in environment (needed by chatbot.py and LLM evaluators)

Run tests:
  pixie-test tests/
  pixie-test tests/ -v               # verbose: per-case scores and reasoning
  pixie-test tests/ -k factuality    # run only factuality test
  pixie-test tests/ -k faithfulness  # run only faithfulness test
  pixie-test tests/ -k relevancy     # run only answer relevancy test
"""

import asyncio
import sys
import os

# Allow import of chatbot from parent dir
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pixie import enable_storage
from pixie.evals import (
    assert_dataset_pass,
    FactualityEval,
    ScoreThreshold,
    last_llm_call,
    root,
)
from pixie.evals import FaithfulnessEval, AnswerRelevancyEval

from chatbot import answer_question

DATASET_NAME = "rag-golden-set"


def runnable(eval_input: dict) -> None:
    """
    Adapter: unpacks eval_input and calls the instrumented answer_question().

    enable_storage() is called here so every test run captures traces
    to the local SQLite DB (needed for from_trace= span selection).
    """
    enable_storage()
    answer_question(**eval_input)


# ---------------------------------------------------------------------------
# Test 1: Factuality — answers must be factually correct vs expected_output
# ---------------------------------------------------------------------------

async def test_factuality():
    """
    FactualityEval checks whether the LLM's answer is factually consistent
    with the expected_output stored in each dataset item.

    Pass criteria: 80% of cases must score >= 0.7.
    The no-context case (Japan capital) is intentionally hard — we allow 20% failures.
    """
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name=DATASET_NAME,
        evaluators=[FactualityEval()],
        pass_criteria=ScoreThreshold(threshold=0.7, pct=0.8),
        from_trace=last_llm_call,
    )


# ---------------------------------------------------------------------------
# Test 2: Faithfulness — answers must be grounded in retrieved context
# ---------------------------------------------------------------------------

async def test_faithfulness():
    """
    FaithfulnessEval checks whether the answer is supported by the context
    that was retrieved and passed to the LLM. Catches hallucinations.

    Evaluated on the last LLM call (where context + question are the input).
    Pass criteria: 80% of cases must score >= 0.7.
    """
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name=DATASET_NAME,
        evaluators=[FaithfulnessEval()],
        pass_criteria=ScoreThreshold(threshold=0.7, pct=0.8),
        from_trace=last_llm_call,
    )


# ---------------------------------------------------------------------------
# Test 3: Answer relevancy — answers must address the question asked
# ---------------------------------------------------------------------------

async def test_answer_relevancy():
    """
    AnswerRelevancyEval checks whether the answer is relevant to the question,
    regardless of factual accuracy. A relevant "I don't know" scores well here.

    Evaluated over the full pipeline (root span) so eval_input contains the question.
    Pass criteria: 90% of cases must score >= 0.6.
    """
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name=DATASET_NAME,
        evaluators=[AnswerRelevancyEval()],
        pass_criteria=ScoreThreshold(threshold=0.6, pct=0.9),
        from_trace=root,
    )
