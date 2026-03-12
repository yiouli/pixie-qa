## Project: Q&A App Eval Debug

### Entry point
`python -c "from qa_app import main; main('...', context='...')"`

### Instrumented spans
- `answer_question(question, context)` — `@observe(name="answer_question")` wraps the full pipeline
  - `eval_input`: `{"question": str, "context": str}`
  - `eval_output`: str (the answer from the LLM)
  - Uses Anthropic `claude-haiku-4-5-20251001` internally

### Datasets
- `qa-golden-set`: 3 items, factual QA, all have `expected_output` set, but `eval_output` is `null` (no pre-captured app outputs)

### Eval plan
- Evaluator: `FactualityEval`
- Pass criteria: `ScoreThreshold(0.7, pct=0.8)`
- Test file: `tests/test_qa.py::test_factuality`
- `from_trace`: `last_llm_call` (required — see root cause below)

---

### Root Cause of Failures

**The `from_trace` parameter was missing from `assert_dataset_pass`.**

The dataset items all have `eval_output: null` — no pre-captured outputs exist. When `assert_dataset_pass` runs the `runnable`, it captures a live trace. The `from_trace` parameter tells the harness which span's output to use for evaluation (`last_llm_call` = the LLM response).

Without `from_trace`, the harness had no live output to evaluate, so `FactualityEval` was comparing `null` against `expected_output` — resulting in low/zero scores.

### Fix Applied
Added `from_trace=last_llm_call` to the `assert_dataset_pass` call in `tests/test_qa.py`.

Import added: `from pixie.evals import ..., last_llm_call`

### How to re-run
```bash
cd /home/yiouli/repo/pixie-qa/.claude/skills/eval-driven-dev-workspace/iteration-3/eval-debug-failures/with_skill/project
PYTHONPATH=/home/yiouli/repo/pixie-qa pixie-test tests/test_qa.py -v
```
