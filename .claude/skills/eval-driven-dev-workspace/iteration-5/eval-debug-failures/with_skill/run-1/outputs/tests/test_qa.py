"""Eval-based tests for the Q&A app."""

import os
import sys

# Ensure the project root is on sys.path so qa_app can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pixie import enable_storage
from pixie.dataset.store import DatasetStore
from pixie.evals import FactualityEval, ScoreThreshold, last_llm_call
from pixie.evals.eval_utils import run_and_evaluate
from pixie.evals.evaluation import Evaluation

from qa_app import answer_question


def runnable(eval_input):
    """Replay one dataset item through the app. enable_storage() ensures traces are captured."""
    enable_storage()
    question = eval_input.get("question", "") if isinstance(eval_input, dict) else str(eval_input)
    context = eval_input.get("context", "") if isinstance(eval_input, dict) else ""
    answer_question(question=question, context=context)


async def test_factuality():
    """Test that answers are factually accurate compared to expected outputs.

    Root cause of original failure: assert_dataset_pass passes evaluables=items
    to assert_pass, which skips trace capture entirely and evaluates the stored
    eval_output (null in dataset) instead of the live app output.

    Fix: load dataset items manually, run_and_evaluate per item injecting
    expected_output so FactualityEval can compare live LLM output against the
    reference answer.
    """
    dataset_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "pixie_datasets",
    )
    store = DatasetStore(dataset_dir=dataset_dir)
    dataset = store.get("qa-golden-set")
    items = list(dataset.items)

    evaluator = FactualityEval()
    all_evals: list[list[list[Evaluation]]] = [[]]

    for item in items:
        evaluation = await run_and_evaluate(
            evaluator=evaluator,
            runnable=runnable,
            eval_input=item.eval_input,
            expected_output=item.expected_output,
            from_trace=last_llm_call,
        )
        all_evals[0].append([evaluation])

    criteria = ScoreThreshold(threshold=0.7, pct=0.8)
    passed, message = criteria(all_evals)
    assert passed, message
