"""Eval-based tests for the Q&A app — fixed to properly capture and evaluate outputs."""

import asyncio
from pixie import enable_storage
from pixie.evals import assert_pass, FactualityEval, ScoreThreshold
from pixie.dataset.store import DatasetStore

from qa_app import answer_question


def runnable(eval_input):
    enable_storage()
    question = eval_input.get("question", "") if isinstance(eval_input, dict) else str(eval_input)
    context = eval_input.get("context", "") if isinstance(eval_input, dict) else ""
    answer_question(question=question, context=context)


async def test_factuality():
    """Test that answers are factually accurate compared to expected outputs."""
    store = DatasetStore()
    dataset = store.get("qa-golden-set")
    items = list(dataset.items)
    eval_inputs = [item.eval_input for item in items]

    # Build per-item evaluators that each have the expected_output baked in
    # by wrapping FactualityEval to merge expected_output from the dataset item.
    from pixie.evals import run_and_evaluate, EvalAssertionError
    from pixie.evals.evaluation import Evaluation

    results = []
    for item in items:
        result = await run_and_evaluate(
            evaluator=FactualityEval(),
            runnable=runnable,
            eval_input=item.eval_input,
            expected_output=item.expected_output,
        )
        results.append(result)

    all_scores = [r.score for r in results]
    avg = sum(all_scores) / len(all_scores) if all_scores else 0.0
    pct_passing = sum(1 for s in all_scores if s >= 0.7) / len(all_scores) if all_scores else 0.0
    passed = pct_passing >= 0.8
    message = f"Average score: {avg:.2f}, pct >= 0.7: {pct_passing:.0%}: {passed}"
    if not passed:
        raise EvalAssertionError(message, results=[[[r] for r in results]])
