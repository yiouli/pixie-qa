# Project: RAG Chatbot Eval

## Entry point
`python chatbot.py` — runs `main()` which calls `answer_question()` for 3 sample questions.

Interactive use: `from chatbot import answer_question; answer_question("What is the capital of France?")`

## Source structure
- `chatbot.py`: single file
  - `retrieve_docs(query)` — stub vector DB, keyword-matches to return doc chunks
  - `answer_question(question)` — retrieves context, calls Claude claude-haiku-4-5-20251001, returns answer string
  - `main()` — demo loop over 3 questions

## Instrumented spans
- `answer_question(question: str)` — @observe wraps the full RAG pipeline
  - eval_input: {"question": str}
  - eval_output: str (the LLM's answer)
- `retrieve_docs(query: str)` — @observe wraps retrieval step (optional, for debugging)
  - eval_input: {"query": str}
  - eval_output: list[str] (retrieved chunks)

## Datasets
- `rag-golden-set`: 8 items covering normal cases, edge cases, and no-context cases
  - Items include expected_output for factuality checking

## Eval plan
- Primary evaluators:
  - `FactualityEval` — checks answer is factually correct vs expected
  - `FaithfulnessEval` — checks answer stays faithful to retrieved context
  - `AnswerRelevancyEval` — checks answer is relevant to the question
- Span: `last_llm_call` for LLM-specific checks, `root` for full pipeline
- Pass criteria: `ScoreThreshold(0.7, pct=0.8)` (80% of cases must score >= 0.7)
- Test file: `tests/test_rag_chatbot.py`

## Dataset items

| # | Question | Expected answer |
|---|----------|----------------|
| 1 | What is the capital of France? | Paris |
| 2 | What is the capital of Germany? | Berlin |
| 3 | What language do people speak in Germany? | German |
| 4 | What language do people speak in France? | French |
| 5 | What is the population of France? | About 68 million |
| 6 | What is the population of Germany? | About 84 million |
| 7 | What languages are spoken in Austria? | German |
| 8 | What is the capital of Japan? | (no relevant docs — expect "I don't know" or similar) |

## Known issues / findings
- `retrieve_docs` is keyword-based — misses semantically related queries
- No-context case ("capital of Japan") retrieves `["No relevant documents found."]`
- The LLM should ideally say it doesn't know for the no-context case
- Uses Anthropic client directly (no LangChain/LlamaIndex wrapper)
