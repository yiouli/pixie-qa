# Eval Pipeline Setup Summary — RAG Chatbot

## What was done

### Stage 1: Explored the codebase
- Read `chatbot.py`: a single-file RAG chatbot using `anthropic` (Claude claude-haiku-4-5-20251001)
- Entry point: `answer_question(question: str) -> str`
- Retrieval: `retrieve_docs(query)` — keyword-based stub returning 1–2 doc chunks
- Data flow: question → retrieved chunks → LLM prompt → answer string

### Stage 2: Decided what to evaluate
- **FactualityEval** — answers must match expected outputs (requires `expected_output` in dataset)
- **FaithfulnessEval** — answers must be grounded in retrieved context (no hallucinations)
- **AnswerRelevancyEval** — answers must address the question asked
- Span: `last_llm_call` for factuality/faithfulness, `root` for answer relevancy
- Pass criteria: `ScoreThreshold(0.7, pct=0.8)` for factuality and faithfulness; `ScoreThreshold(0.6, pct=0.9)` for relevancy

### Stage 3: Instrumented `chatbot.py`
Added to `chatbot.py`:
- `from pixie import enable_storage` + `import pixie.instrumentation as px`
- `@px.observe(name="retrieve_docs")` on `retrieve_docs()`
- `@px.observe(name="answer_question")` on `answer_question()`
- `enable_storage()` at the top of `main()`
- `px.flush()` at the end of `main()` to ensure spans are written

### Stage 4: Built dataset `rag-golden-set`
Created `build_dataset.py` — run with `python build_dataset.py` to populate the dataset.

8 items covering:
- Normal cases (capitals, languages, populations of France/Germany)
- Indirect case (Austria's language — in context but not directly asked)
- No-context / out-of-domain case (capital of Japan — no docs retrieved)

All items include `expected_output` for use by `FactualityEval`.

### Stage 5: Wrote test file
Created `tests/test_rag_chatbot.py` with 3 async test functions:
- `test_factuality` — FactualityEval on last_llm_call, 80% @ 0.7
- `test_faithfulness` — FaithfulnessEval on last_llm_call, 80% @ 0.7
- `test_answer_relevancy` — AnswerRelevancyEval on root span, 90% @ 0.6

## Files created/modified

| File | Action |
|------|--------|
| `project/chatbot.py` | Modified — added pixie imports, `@px.observe` decorators, `enable_storage()`, `px.flush()` |
| `project/MEMORY.md` | Created — eval notes and plan |
| `project/build_dataset.py` | Created — programmatic dataset builder |
| `project/tests/test_rag_chatbot.py` | Created — 3 eval test functions |

## How to run

```bash
# 1. Set API key
export ANTHROPIC_API_KEY=sk-...

# 2. Build the dataset
cd project
python build_dataset.py

# 3. Run all tests
pixie-test tests/

# 4. Run verbose (see per-case scores)
pixie-test tests/ -v

# 5. Run a single test
pixie-test tests/ -k factuality
```

## Key findings
- The stub retriever is keyword-based — queries without exact keywords ("capital", "population", "language") return `["No relevant documents found."]`
- The no-context case (Japan) is the hardest — the model must resist hallucinating and say it doesn't know
- Faithfulness should be high for in-domain cases since context directly contains the answers
- The Austria case tests whether the model reads context carefully (answer is present in the German language chunk)
