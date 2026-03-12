# Setting Up an Eval Pipeline for Your RAG Chatbot with Pixie

You have a Python chatbot that retrieves document chunks and generates answers with Claude. The core risk is prompt regression: you tweak a prompt, manually check it looks okay, but something subtler breaks elsewhere. A systematic eval pipeline with pixie solves this by making regressions visible before you ship.

Here is a practical, step-by-step guide.

---

## Step 1: Instrument Your Chatbot

Pixie needs to observe what your app is doing. Wrap your chatbot's entry point with `px.start_observation` so every run produces a trace.

```python
import pixie.instrumentation as px
from pixie import enable_storage

# One-time setup — creates SQLite DB and registers the storage handler
enable_storage()
px.init()

def answer_question(question: str) -> str:
    with px.start_observation(input=question, name="rag-chatbot") as obs:
        # Your existing retrieval + generation logic
        chunks = retrieve_chunks(question)
        answer = generate_answer(question, chunks)
        obs.set_output(answer)
        # Optionally record retrieved context for faithfulness eval
        obs.set_metadata("retrieved_chunks", chunks)
    return answer
```

If you call Claude (or any LLM) via the Anthropic SDK, the LLM span is captured automatically. The `enable_storage()` call means every observation is persisted to SQLite without any extra wiring.

---

## Step 2: Build a Golden Dataset

A golden dataset is a curated set of (question, expected answer) pairs that represent the breadth of queries your chatbot must handle. Collect them from real user queries, edge cases you know about, and any failure modes you have seen.

```python
from pixie.dataset import DatasetStore
from pixie.storage.evaluable import Evaluable

store = DatasetStore()

store.create("rag-chatbot-golden", items=[
    Evaluable(
        eval_input="What is our refund policy for digital products?",
        expected_output="Digital products are non-refundable after download.",
    ),
    Evaluable(
        eval_input="How do I reset my password?",
        expected_output="Go to the login page and click 'Forgot password'.",
    ),
    Evaluable(
        eval_input="What are the supported payment methods?",
        expected_output="We accept Visa, Mastercard, and PayPal.",
    ),
    # Add 10–30 more representative cases
])
```

You can also save real traces from production runs directly to a dataset using the CLI:

```bash
# After running your chatbot once interactively, save the trace
pixie dataset save rag-chatbot-golden --notes "real user query about refunds"
echo '"Digital products are non-refundable after download."' | pixie dataset save rag-chatbot-golden --expected-output
```

This makes it easy to build your dataset from actual traffic rather than purely synthetic examples.

---

## Step 3: Choose the Right Evaluators

For a RAG chatbot, three dimensions matter most:

| Dimension | Evaluator | What it checks |
|---|---|---|
| Factual accuracy | `FactualityEval` | Does the answer match the expected fact? |
| Faithfulness to retrieved context | `FaithfulnessEval` | Does the answer stay grounded in the chunks? |
| Answer relevancy | `AnswerRelevancyEval` | Does the answer address what was asked? |
| Answer correctness (end-to-end) | `AnswerCorrectnessEval` | Is the full answer correct relative to ground truth? |

The RAG-specific evaluators (`ContextRelevancyEval`, `FaithfulnessEval`, `AnswerRelevancyEval`, `AnswerCorrectnessEval`) are RAGAS-based and built into pixie. They are the most important ones for your use case because they test the retrieval-generation pipeline holistically.

For quick sanity checks without LLM costs, `EmbeddingSimilarityEval` is a useful heuristic.

---

## Step 4: Write Your Eval Test

Put this in a file like `tests/test_rag_chatbot_eval.py`:

```python
import pytest
from pixie.evals import (
    assert_dataset_pass,
    ScoreThreshold,
)
from pixie.evals import (
    FactualityEval,
    FaithfulnessEval,
    AnswerRelevancyEval,
    AnswerCorrectnessEval,
)
from my_chatbot import answer_question  # your instrumented function


@pytest.mark.asyncio
async def test_factual_accuracy():
    """Answers must be factually correct relative to expected outputs."""
    await assert_dataset_pass(
        runnable=answer_question,
        dataset_name="rag-chatbot-golden",
        evaluators=[FactualityEval()],
        pass_criteria=ScoreThreshold(threshold=0.7, pct=0.9),  # 90% of cases must score >= 0.7
    )


@pytest.mark.asyncio
async def test_answer_correctness():
    """End-to-end correctness combining factuality and answer relevancy."""
    await assert_dataset_pass(
        runnable=answer_question,
        dataset_name="rag-chatbot-golden",
        evaluators=[AnswerCorrectnessEval()],
        pass_criteria=ScoreThreshold(threshold=0.6, pct=0.85),
    )


@pytest.mark.asyncio
async def test_faithfulness():
    """Answers must not hallucinate beyond what the retrieved chunks say."""
    await assert_dataset_pass(
        runnable=answer_question,
        dataset_name="rag-chatbot-golden",
        evaluators=[FaithfulnessEval()],
        pass_criteria=ScoreThreshold(threshold=0.8, pct=0.95),  # Strict — hallucination is bad
    )
```

The `ScoreThreshold(threshold=X, pct=Y)` parameters let you set realistic bars: not every answer needs to be perfect, but you want to catch systematic regressions.

---

## Step 5: Run the Evals

```bash
# Run all eval tests
pixie-test tests/

# Run just the RAG evals with verbose output
pixie-test tests/test_rag_chatbot_eval.py -v

# Filter to a specific test
pixie-test tests/ -k faithfulness
```

Or with pytest directly:

```bash
uv run pytest tests/test_rag_chatbot_eval.py -v
```

---

## Step 6: Iterate and Expand the Dataset

When you catch a regression, add it to your dataset:

```bash
# Run your chatbot manually on the failing case
python -c "from my_chatbot import answer_question; answer_question('What is your cancellation policy?')"

# Save the trace to your dataset with the correct expected output
pixie dataset save rag-chatbot-golden --notes "cancellation policy - was hallucinating"
echo '"You can cancel any subscription within 14 days for a full refund."' | pixie dataset save rag-chatbot-golden --expected-output
```

This turns every bug you find manually into a permanent regression test.

---

## Step 7: Integrate into CI

Add this to your CI pipeline (e.g., GitHub Actions):

```yaml
- name: Run eval pipeline
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}  # needed for LLM-as-judge evaluators
    PIXIE_DB_PATH: /tmp/pixie_eval.db
    PIXIE_DATASET_DIR: ./pixie_datasets
  run: |
    uv run pixie-test tests/test_rag_chatbot_eval.py -v
```

The key environment variables:
- `PIXIE_DB_PATH` — where traces are stored during the eval run (use a temp path in CI)
- `PIXIE_DATASET_DIR` — where your golden dataset JSON files live (commit this directory to your repo)
- `OPENAI_API_KEY` — the LLM-as-judge evaluators (FactualityEval, etc.) call OpenAI by default

---

## Practical Tips for RAG Evals

**Start with 10–15 golden cases, not 100.** A small, high-quality dataset that covers your key doc categories is more valuable than a large noisy one.

**Tune thresholds empirically.** Run your eval suite on your current prompt first to establish a baseline. Set your `ScoreThreshold` just below your current score so the test passes today but would catch meaningful drops.

**Separate retrieval from generation concerns.** You can write one test that checks whether the right chunks were retrieved (using `ContextRelevancyEval`) and another that checks whether the generation was faithful to whatever chunks it got (using `FaithfulnessEval`). This pinpoints whether a regression is a retrieval problem or a prompting problem.

**Use `last_llm_call` when you care about the raw LLM output.** If your chatbot does post-processing after the LLM call, use `from_trace=last_llm_call` in `assert_pass` to evaluate the LLM output before post-processing:

```python
from pixie.evals import assert_dataset_pass, last_llm_call

await assert_dataset_pass(
    runnable=answer_question,
    dataset_name="rag-chatbot-golden",
    evaluators=[FactualityEval()],
    from_trace=last_llm_call,
)
```

**Keep your dataset in version control.** The `pixie_datasets/` directory contains JSON files. Commit them. This means your golden test cases travel with your code and every PR can be evaluated against the same ground truth.

---

## Summary

The workflow is:

1. Instrument your chatbot with `px.start_observation` and `enable_storage()`
2. Build a golden dataset of (question, expected_answer) pairs with `DatasetStore`
3. Write pytest tests using `assert_dataset_pass` with RAG-appropriate evaluators (`FaithfulnessEval`, `FactualityEval`, `AnswerCorrectnessEval`)
4. Set `ScoreThreshold` based on your current baseline performance
5. Run with `pixie-test` locally and in CI
6. When you find new bugs, save them to the dataset so they become permanent regression tests

This gives you a living eval suite that grows as your chatbot evolves, catches prompt regressions automatically, and lets you ship prompt changes with confidence.
