"""Eval tests for the RAG chatbot using pixie."""

from pixie import enable_storage
from pixie.evals import assert_dataset_pass, ExactMatchEval, ScoreThreshold
from pixie.evals import root

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chatbot import answer_question


def runnable(eval_input):
    """Adapter: call answer_question with the captured eval_input."""
    enable_storage()
    answer_question(**eval_input)


async def test_answer_exactmatch():
    """Test that answers exactly match expected outputs for known questions."""
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name="rag-chatbot-golden",
        evaluators=[ExactMatchEval()],
        pass_criteria=ScoreThreshold(threshold=1.0, pct=0.75),
        from_trace=root,
    )
