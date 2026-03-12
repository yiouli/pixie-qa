"""Eval-based tests for the Q&A app."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pixie.instrumentation as px
from pixie.dataset.store import DatasetStore
from pixie.evals import (
    FactualityEval,
    ScoreThreshold,
    assert_pass,
    capture_traces,
    last_llm_call,
)
from pixie.storage.evaluable import Evaluable
from pixie.storage.tree import build_tree

from qa_app import answer_question


def _run_one(eval_input) -> str:
    """Run the Q&A app for one dataset item and return the answer text."""
    question = eval_input.get("question", "") if isinstance(eval_input, dict) else str(eval_input)
    context = eval_input.get("context", "") if isinstance(eval_input, dict) else ""
    return answer_question(question=question, context=context)


async def test_factuality():
    """Test that answers are factually accurate compared to expected outputs.

    Root-cause fix: the dataset items have eval_output=null, so evaluators
    were always receiving None as output.  This test now:
      1. Runs the app for each item using capture_traces to get the real
         LLM output from the trace.
      2. Builds Evaluable objects with the live eval_output AND the
         expected_output from the dataset.
      3. Passes those to assert_pass so FactualityEval can compare them.
    """
    px.init()

    dataset_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "pixie_datasets",
    )
    store = DatasetStore(dataset_dir=dataset_dir)
    dataset = store.get("qa-golden-set")
    items = list(dataset.items)

    # Step 1: Run the app for each item and capture the real LLM output.
    live_evaluables: list[Evaluable] = []
    for item in items:
        with capture_traces() as handler:
            _run_one(item.eval_input)

        if not handler.spans:
            raise RuntimeError(
                f"No spans captured for input: {item.eval_input!r}"
            )

        trace_tree = build_tree(handler.spans)
        live_ev = last_llm_call(trace_tree)

        # Step 2: Merge the live eval_output with the dataset's expected_output.
        live_evaluables.append(
            Evaluable(
                eval_input=item.eval_input,
                eval_output=live_ev.eval_output,
                eval_metadata=item.eval_metadata,
                expected_output=item.expected_output,
            )
        )

    # Step 3: Evaluate — runnable is a no-op placeholder since we supply
    # pre-built evaluables; assert_pass will call evaluate() directly.
    await assert_pass(
        runnable=lambda x: None,
        eval_inputs=[item.eval_input for item in items],
        evaluators=[FactualityEval()],
        evaluables=live_evaluables,
        pass_criteria=ScoreThreshold(threshold=0.7, pct=0.8),
    )
