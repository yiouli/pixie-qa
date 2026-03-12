## Project: RAG Chatbot (Mock)

### Entry point
`python chatbot.py` — runs `main()` which calls `answer_question()` for 4 questions.

### Instrumented spans
- `answer_question(question)` — @observe wraps the full RAG pipeline
  - eval_input: {"question": str}
  - eval_output: str (the answer — first retrieved chunk)

### Datasets
- `rag-chatbot-golden`: 4 items covering capital, language, population, currency questions

### Eval plan
- Evaluator: ExactMatchEval (heuristic, no LLM key needed)
- Pass criteria: ScoreThreshold(threshold=1.0, pct=0.75) — 75% of cases must be exact match
- Test file: tests/test_rag_chatbot.py::test_answer_exactmatch
- Uses `root` span since `answer_question` is the outermost observed function

### Known issues / findings
- Mock version: no real LLM calls, answers are deterministic keyword-based retrieval
- `answer_question` returns chunks[0] (first retrieved doc), so expected_output is the first chunk per keyword
