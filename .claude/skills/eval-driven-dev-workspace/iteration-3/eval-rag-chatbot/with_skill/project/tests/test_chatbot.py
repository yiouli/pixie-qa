"""Eval tests for the RAG chatbot using pixie."""
import asyncio
from pixie import enable_storage
from pixie.evals import assert_dataset_pass, FactualityEval, ScoreThreshold, root


def runnable(eval_input):
    """Run the chatbot with eval_input from the dataset."""
    enable_storage()
    from chatbot import answer_question
    answer_question(**eval_input)


async def test_factuality():
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name="rag-chatbot-golden",
        evaluators=[FactualityEval()],
        pass_criteria=ScoreThreshold(threshold=0.7, pct=0.8),
        from_trace=root,
    )
