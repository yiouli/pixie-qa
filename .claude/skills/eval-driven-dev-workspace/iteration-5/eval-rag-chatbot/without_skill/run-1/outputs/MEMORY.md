# RAG Chatbot — Eval-Driven Development Setup

## What was done

### 1. Instrumented `chatbot.py`

Added pixie instrumentation to the two core functions:

- Called `px.init()` at module level to initialise the instrumentation subsystem.
- Decorated `retrieve_docs()` with `@px.observe()` — captures `query` as input and the returned chunk list as output.
- Decorated `answer_question()` with `@px.observe()` — captures `question` as input and the final answer string as output.

Because `answer_question` calls `retrieve_docs`, the two spans are nested: the outer `answer_question` span is the root, and `retrieve_docs` is a child span.

### 2. Golden dataset — `datasets/rag-chatbot-golden.json`

A JSON file conforming to pixie's `Dataset` / `Evaluable` schema.  It contains 6 question-answer pairs covering all four topic keywords (capital, language, population, currency) for both France and Germany.

Each item has:
- `eval_input`: the question string (passed to `answer_question`)
- `expected_output`: the exact string the chatbot is expected to return

Load it with:
```python
from pixie.dataset.store import DatasetStore
store = DatasetStore(dataset_dir="datasets")
dataset = store.get("rag-chatbot-golden")
```

### 3. Eval test file — `test_chatbot_eval.py`

Three test classes:

| Class | Method | Evaluator | Notes |
|---|---|---|---|
| `TestChatbotEvalDataset` | `test_exact_match_golden_dataset` | `ExactMatchEval` | Loads dataset from disk via `assert_dataset_pass` |
| `TestChatbotEvalDataset` | `test_levenshtein_similarity_golden_dataset` | `LevenshteinMatch` | Threshold 0.8 — catches near-misses |
| `TestChatbotEvalInline` | `test_exact_match_inline` | `ExactMatchEval` | Same golden pairs, no file I/O, uses `assert_pass` + inline `Evaluable` list |
| `TestChatbotEvalInline` | `test_unknown_question_returns_fallback` | custom | Verifies fallback message for out-of-scope questions |

## How to run

```bash
# From the project directory
PYTHONPATH=/home/yiouli/repo/pixie-qa pytest test_chatbot_eval.py -v
```

## Key design decisions

- `px.init()` is called at module import time in `chatbot.py`. This is idempotent — calling it again from test fixtures is safe.
- The `_reset_instrumentation` autouse fixture calls `_px_obs._reset_state()` before and after each test to prevent span leakage between tests.
- The `run_chatbot` wrapper imports `answer_question` lazily (inside the function body) so the import happens after any fixture-level state resets.
- `ExactMatchEval` is the primary evaluator because the mock chatbot is fully deterministic; Levenshtein is added as a secondary check to show how threshold-based criteria work.

## Files created / modified

| File | Action |
|---|---|
| `chatbot.py` | Modified — added `px.init()` and `@px.observe()` decorators |
| `datasets/rag-chatbot-golden.json` | Created — 6-item golden dataset |
| `test_chatbot_eval.py` | Created — eval test suite |
| `MEMORY.md` | Created — this file |
