## Project: RAG Chatbot (mock)

### Entry point
`python chatbot.py` — runs 4 questions through the pipeline.

### Instrumented spans
- `answer_question(question)` — `@px.observe(name="answer_question")` wraps the full pipeline
  - eval_input: {"question": str}
  - eval_output: str (the answer)

### Datasets
- `rag-chatbot-golden`: 4 items, one per question, factual QA

### Eval plan
- Evaluator: FactualityEval
- Pass criteria: ScoreThreshold(0.7, pct=0.8)
- Test file: tests/test_chatbot.py::test_factuality

### Commands
```bash
# Run and capture traces
PYTHONPATH=/home/yiouli/repo/pixie-qa python chatbot.py
# Save traces
PYTHONPATH=/home/yiouli/repo/pixie-qa pixie dataset save rag-chatbot-golden
# Run tests
PYTHONPATH=/home/yiouli/repo/pixie-qa pixie-test tests/ -v
```
