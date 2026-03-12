"""Eval tests for the email classifier."""

from pixie import enable_storage
from pixie.evals import assert_dataset_pass, JSONDiffEval, ScoreThreshold, root

from extractor import extract_from_email


def runnable(eval_input):
    """Replay one dataset item through the classifier."""
    enable_storage()
    extract_from_email(**eval_input)


async def test_classification():
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name="email-classifier-golden",
        evaluators=[JSONDiffEval()],
        pass_criteria=ScoreThreshold(threshold=0.8, pct=0.8),
        from_trace=root,
    )
