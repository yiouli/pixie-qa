# Setting Up an Eval Pipeline for Your RAG Chatbot with pixie

This guide walks you through each stage of eval-driven development for a Python RAG chatbot that retrieves document chunks and generates answers using Claude.

---

## Stage 1: Understand Your Application

A typical RAG chatbot has this shape:

```
user question
    → retrieval step (fetch relevant doc chunks)
    → prompt construction (question + chunks)
    → LLM call (Claude generates answer)
    → response to user
```

There are two things you can evaluate:
1. **Retrieval quality** — did you fetch the right chunks?
2. **Answer quality** — given those chunks, did Claude answer correctly and faithfully?

This guide focuses on answer quality (the most common regression source), but also covers retrieval.

---

## Stage 2: Decide What to Evaluate

For a RAG chatbot, the most useful evaluators are:

| What you want to check | Evaluator | Notes |
|---|---|---|
| Answer is faithful to the retrieved context | `FaithfulnessEval` | Catches hallucination; no expected output needed |
| Answer actually addresses the question | `AnswerRelevancyEval` | Catches off-topic or evasive answers |
| Answer is correct vs a known reference | `AnswerCorrectnessEval` | Requires expected output per test case |
| Retrieved context is relevant | `ContextRelevancyEval` | Evaluates retrieval step quality |

**Recommendation for getting started:** Use `FaithfulnessEval` + `AnswerRelevancyEval` first — they require no reference answers and catch the most common regressions (hallucination, topic drift). Add `AnswerCorrectnessEval` once you have a golden set.

**Pass criteria:** `ScoreThreshold(threshold=0.7, pct=0.8)` — require 80% of test cases to score 0.7 or higher. Adjust as your dataset grows.

---

## Stage 3: Instrument the Application

You need pixie to see your function's inputs and outputs. Add instrumentation at the outermost logical boundary — the function that takes a question and returns an answer.

### Step 1: Install and enable storage

```python
# At the top of your app or test file
from pixie import enable_storage
enable_storage()
```

### Step 2: Decorate your answer function

The key is that `@observe` captures kwargs as `eval_input` and the return value as `eval_output`. Design your function signature so that both the question and the retrieved context are kwargs — this lets pixie capture the full picture for evaluation.

```python
import pixie.instrumentation as px

@px.observe(name="answer_question")
def answer_question(question: str, context: str) -> str:
    """
    question: the user's question
    context: concatenated retrieved document chunks
    """
    # your existing Claude call goes here
    response = claude_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        messages=[
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ],
        max_tokens=1024,
    )
    return response.content[0].text
```

If your current code retrieves docs inside the same function, that's fine — `context` will be captured as whatever you pass in. If retrieval is a separate step, call it before and pass the result as `context`.

After each run, flush to ensure spans are written:

```python
import pixie.instrumentation as px
px.flush()
```

---

## Stage 4: Build a Dataset

### First run: capture one real trace

Run your app on a representative question to see what the data looks like:

```python
from pixie import enable_storage
import pixie.instrumentation as px

enable_storage()

# Run your app
answer = answer_question(
    question="How do I reset my password?",
    context="To reset your password, go to Settings > Security > Reset Password..."
)
print(answer)
px.flush()
```

Then create a dataset and save the trace:

```bash
pixie dataset create rag-golden-set
pixie dataset save rag-golden-set --notes "password reset question"
```

If you know the correct answer, attach it as expected output:

```bash
echo '"Navigate to Settings > Security and click Reset Password."' | \
  pixie dataset save rag-golden-set --expected-output
```

### Build up the dataset with varied cases

Aim for 10–20 test cases covering:
- Questions with clear answers in the docs
- Questions where the answer spans multiple chunks
- Questions where the docs don't contain the answer (should say "I don't know")
- Questions with ambiguous wording

Run your app for each case and save:

```bash
# after each run:
pixie dataset save rag-golden-set --notes "multi-chunk answer case"
```

### Alternative: generate synthetic data programmatically

If you have many doc topics and want coverage without running each manually:

```python
from pixie import enable_storage
import pixie.instrumentation as px
from pixie.dataset.store import DatasetStore
from pixie.storage.evaluable import Evaluable

enable_storage()

test_cases = [
    {
        "question": "What are the password requirements?",
        "context": "Passwords must be at least 12 characters...",
        "expected": "Passwords must be at least 12 characters long.",
    },
    {
        "question": "How do I contact support?",
        "context": "You can reach support at support@example.com or call 1-800-555-0100.",
        "expected": "Contact support by email at support@example.com or by phone at 1-800-555-0100.",
    },
    # add more cases...
]

store = DatasetStore()
store.create("rag-golden-set")

for case in test_cases:
    store.append("rag-golden-set", Evaluable(
        eval_input={"question": case["question"], "context": case["context"]},
        expected_output=case["expected"],
    ))
```

---

## Stage 5: Write and Run Eval Tests

Create a test file in your project:

```python
# tests/test_rag_chatbot.py
import asyncio
from pixie import enable_storage
from pixie.evals import (
    assert_dataset_pass,
    FaithfulnessEval,
    AnswerRelevancyEval,
    AnswerCorrectnessEval,
    ScoreThreshold,
    last_llm_call,
)

from my_chatbot import answer_question  # your instrumented function


def runnable(eval_input):
    """Adapter: unpack the dataset item's input dict and call the app."""
    enable_storage()
    answer_question(**eval_input)


async def test_faithfulness():
    """Answer must not hallucinate facts not in the retrieved context."""
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name="rag-golden-set",
        evaluators=[FaithfulnessEval()],
        pass_criteria=ScoreThreshold(threshold=0.7, pct=0.8),
        from_trace=last_llm_call,
    )


async def test_answer_relevancy():
    """Answer must actually address the question asked."""
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name="rag-golden-set",
        evaluators=[AnswerRelevancyEval()],
        pass_criteria=ScoreThreshold(threshold=0.7, pct=0.8),
        from_trace=last_llm_call,
    )


async def test_answer_correctness():
    """Answer must match the reference answer (requires expected_output in dataset)."""
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name="rag-golden-set",
        evaluators=[AnswerCorrectnessEval()],
        pass_criteria=ScoreThreshold(threshold=0.7, pct=0.8),
        from_trace=last_llm_call,
    )
```

Run the tests:

```bash
pixie-test tests/                   # run all tests
pixie-test -k faithfulness          # run only the faithfulness test
pixie-test -v                       # verbose output with failure details
```

---

## Stage 6: Investigate Failures

When a test fails, `pixie-test -v` prints an `EvalAssertionError` with scores and reasoning for every case. Look for patterns:

- Multiple failures with low faithfulness? Your prompt may be allowing the model to go beyond the context.
- Low answer relevancy? The retrieval may be returning off-topic chunks.
- Specific questions failing? Check what context was retrieved for those questions.

To inspect a specific failing trace:

```python
import asyncio
from pixie.storage.store import ObservationStore

async def inspect(trace_id: str):
    store = ObservationStore()
    roots = await store.get_trace(trace_id)
    for root in roots:
        print(root.to_text())

asyncio.run(inspect("paste-trace-id-here"))
```

The `trace_id` is stored in `eval_metadata` on each dataset item after a test run.

---

## Stage 7: Iterate

The typical loop after a failure:

1. Identify what's failing (faithfulness? relevancy? specific doc topics?)
2. Make a targeted change — update the system prompt, adjust chunk size, change retrieval parameters
3. Re-run `pixie-test` and compare
4. If you added a new scenario, add it to the dataset before re-running

**Guarding against regressions:** Run `pixie-test` in CI on every prompt change. The dataset is your regression suite — each time you fix a bug, add a test case for it.

---

## Quick-Start Checklist

- [ ] Add `enable_storage()` at app startup
- [ ] Wrap your answer function with `@px.observe(name="answer_question")`
- [ ] Ensure function signature uses `question` and `context` as kwargs
- [ ] Call `px.flush()` after each run
- [ ] `pixie dataset create rag-golden-set`
- [ ] Run 10–20 varied test cases and save each with `pixie dataset save`
- [ ] Add expected outputs for cases where you know the right answer
- [ ] Create `tests/test_rag_chatbot.py` with faithfulness + relevancy tests
- [ ] Run `pixie-test tests/` and fix failures
- [ ] Add `pixie-test` to your CI pipeline

---

## Key pixie APIs for RAG

```python
# Instrumentation
from pixie import enable_storage
import pixie.instrumentation as px

enable_storage()

@px.observe(name="answer_question")
def answer_question(question: str, context: str) -> str: ...

px.flush()

# Evaluators (import from pixie.evals)
FaithfulnessEval()          # answer faithful to context — no expected output needed
AnswerRelevancyEval()       # answer addresses the question — no expected output needed
AnswerCorrectnessEval()     # answer correct vs reference — needs expected_output
ContextRelevancyEval()      # retrieved context is relevant — evaluates retrieval step

# Pass criteria
ScoreThreshold(threshold=0.7, pct=0.8)   # 80% of cases must score >= 0.7

# Trace selector
from_trace=last_llm_call    # evaluate the LLM span (most useful for RAG)
from_trace=root             # evaluate the @observe wrapper span
```
