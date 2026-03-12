"""Eval-based tests for the Q&A app — fixed."""

import asyncio
from pixie import enable_storage
from pixie.evals import assert_pass, FactualityEval, ScoreThreshold
from pixie.dataset.store import DatasetStore
from pixie.storage.evaluable import Evaluable

from qa_app import answer_question


def runnable(eval_input):
    enable_storage()
    question = eval_input.get("question", "") if isinstance(eval_input, dict) else str(eval_input)
    context = eval_input.get("context", "") if isinstance(eval_input, dict) else ""
    return answer_question(question=question, context=context)


async def test_factuality():
    """Test that answers are factually accurate compared to expected outputs."""
    store = DatasetStore()
    dataset = store.get("qa-golden-set")
    items = list(dataset.items)

    # Run the runnable for each item to get live eval_output, then build evaluables
    populated_evaluables = []
    for item in items:
        output = await asyncio.to_thread(runnable, item.eval_input)
        populated_evaluables.append(
            Evaluable(
                eval_input=item.eval_input,
                eval_output=output,
                eval_metadata=item.eval_metadata,
                expected_output=item.expected_output,
            )
        )

    await assert_pass(
        runnable=runnable,
        eval_inputs=[item.eval_input for item in items],
        evaluators=[FactualityEval()],
        evaluables=populated_evaluables,
        pass_criteria=ScoreThreshold(threshold=0.7, pct=0.8),
    )
