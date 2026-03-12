## Project: RAG Chatbot (mock)

### Entry point
`python chatbot.py` — runs 4 sample questions through `answer_question`.
`answer_question(question: str) -> str` — the main function to evaluate.

### How the app works
- `retrieve_docs(query)`: keyword-matches the query against a small in-memory document store and returns matching chunks.
- `answer_question(question)`: calls `retrieve_docs`, returns the first retrieved chunk as the answer. In a real version this would call an LLM; here it's a deterministic mock.
- No real LLM calls are made, so there is no `last_llm_call` span in traces. Evaluation uses `from_trace=root`.

### Instrumented spans
- `answer_question(question)` — `@px.observe(name="answer_question")` wraps the full pipeline.
  - `eval_input`: `{"question": str}`
  - `eval_output`: `str` (the answer, i.e. the first retrieved chunk)
- `enable_storage()` is called at module import time (chatbot.py top-level) and also inside the test `runnable` to ensure traces are always captured.

### Datasets
- `rag-chatbot-golden`: golden dataset with 4 factual QA items covering capitals, language, population, and currency questions. Each item has an `expected_output`.

### Dataset items
| question | expected_output |
|---|---|
| What is the capital of France? | Paris |
| What language do people speak in Germany? | German |
| What is the population of France? | 68 million (approx) |
| What currency does Germany use? | Euro (EUR) |

### Eval plan
- **Evaluators**: `FactualityEval` (factual accuracy vs expected output), `AnswerRelevancyEval` (answer is relevant to the question)
- **Pass criteria**: `ScoreThreshold(0.7, pct=0.8)` — 80% of cases must score ≥ 0.7
- **from_trace**: `root` (no LLM span exists in mock)
- **Test file**: `tests/test_rag_chatbot.py`

### Commands

```bash
# Set PYTHONPATH for pixie
export PYTHONPATH=/home/yiouli/repo/pixie-qa

# Run the app to generate traces (from project dir)
cd /home/yiouli/repo/pixie-qa/.claude/skills/eval-driven-dev-workspace/iteration-5/eval-rag-chatbot/with_skill/project
python chatbot.py

# Create the dataset
pixie dataset create rag-chatbot-golden

# Save each run trace with expected output (run chatbot once per question then save)
python -c "from chatbot import answer_question; answer_question('What is the capital of France?')"
echo '"Paris"' | pixie dataset save rag-chatbot-golden --expected-output --notes "capital of France"

python -c "from chatbot import answer_question; answer_question('What language do people speak in Germany?')"
echo '"German"' | pixie dataset save rag-chatbot-golden --expected-output --notes "language in Germany"

python -c "from chatbot import answer_question; answer_question('What is the population of France?')"
echo '"France has a population of about 68 million."' | pixie dataset save rag-chatbot-golden --expected-output --notes "population of France"

python -c "from chatbot import answer_question; answer_question('What currency does Germany use?')"
echo '"Euro (EUR)"' | pixie dataset save rag-chatbot-golden --expected-output --notes "currency of Germany"

# Verify dataset
pixie dataset list

# Run eval tests
pixie-test tests/ -v
```

### Known issues / findings
- The app is a deterministic mock — no real LLM is used. Answers are the first retrieved chunk verbatim.
- `from_trace=root` is used because there is no LLM span; `last_llm_call` would fail or return nothing.
- The golden dataset is built programmatically (see build_dataset.py) to avoid manual CLI steps.
