# Eval Pipeline Setup — RAG Chatbot

## What was done

### 1. Instrumentation (`chatbot.py`)

- Added `import pixie.instrumentation as px` and a module-level `px.init()` call.
- Wrapped the body of `answer_question()` with `px.start_observation(input=question, name="rag-chatbot")`.
- Inside the observation:
  - Called `observation.set_metadata("retrieved_chunks", ...)` and `observation.set_metadata("context", ...)` to record what was retrieved.
  - Called `observation.set_output(answer)` so the final LLM answer is attached to the span.
- Added `px.flush()` after the `with` block so spans are delivered synchronously before the function returns.

### 2. Dataset (`build_dataset.py`)

- Created `build_dataset.py` which uses `DatasetStore` + `Evaluable` to programmatically build a golden-set dataset named `rag-chatbot-golden-set`.
- 6 items covering the three knowledge topics available in the stub retriever:
  - Capital of France → "Paris"
  - Capital of Germany → "Berlin"
  - Language in France → "French"
  - Language in Germany → "German"
  - Population of France → "about 68 million"
  - Population of Germany → "about 84 million"
- Script is idempotent: it deletes an existing dataset of the same name before re-creating it.

### 3. Tests (`test_chatbot.py`)

Five pytest-asyncio tests covering:

| Test | Evaluator used | What it checks |
|------|---------------|----------------|
| `test_answer_is_non_empty` | custom `non_empty_evaluator` | Chatbot always returns a non-empty string |
| `test_capital_questions_contain_expected_city` | custom `contains_answer_evaluator` | Answers for capital questions contain the right city |
| `test_language_questions_contain_expected_language` | custom `contains_answer_evaluator` | Answers for language questions contain the right language |
| `test_levenshtein_capital_france` | `LevenshteinMatch` | String similarity to expected answer is > 0 |
| `test_dataset_golden_set` | custom `contains_answer_evaluator` + `ScoreThreshold` | Full golden-set dataset passes at 80 % threshold |

An additional test `test_llm_call_captured_in_trace` verifies that the LLM span can be accessed via `last_llm_call` trace extractor.

## How to run

```bash
# 1. Build the dataset (one-time or whenever you want to reset it)
python build_dataset.py

# 2. Run the tests (requires ANTHROPIC_API_KEY)
pixie-test test_chatbot.py -v
# or
pytest test_chatbot.py -v
```
