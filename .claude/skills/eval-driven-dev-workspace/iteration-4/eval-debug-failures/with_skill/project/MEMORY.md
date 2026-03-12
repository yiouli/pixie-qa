## Project: Q&A App Eval Debug

### Entry point
`from qa_app import main; main(question, context)` or directly `answer_question(question, context)`

### Instrumented spans
- `answer_question(question, context)` — decorated with `@px.observe(name="answer_question")`
  - eval_input: `{"question": str, "context": str}`
  - eval_output: str (the LLM response)
- The function calls Anthropic Claude (claude-haiku-4-5-20251001) and returns the response text.

### Datasets
- `qa-golden-set`: 3 items covering factual QA (geography, literature, science)
  - All items have `expected_output` set
  - All items had `eval_output: null` (pre-populated traces were missing)

### Eval plan
- Evaluator: `FactualityEval()`
- Pass criteria: `ScoreThreshold(threshold=0.7, pct=0.8)` (80% of cases must score ≥ 0.7)
- Test file: `tests/test_qa.py::test_factuality`
- `from_trace`: `last_llm_call` — captures live LLM response during each test run

### Root Cause of Failures

The dataset `pixie_datasets/qa-golden-set.json` had `"eval_output": null` for all 3 items.
`FactualityEval` compares `eval_output` against `expected_output`, but with null outputs there
is nothing to evaluate — all cases scored 0.

The test was missing `from_trace=last_llm_call` in the `assert_dataset_pass` call. Without this
argument, the harness uses the stored `eval_output` from the dataset (null). With `from_trace=last_llm_call`,
the harness re-runs the app for each dataset item, captures the live LLM response from the trace,
and evaluates that instead.

### Fix Applied
Added `from_trace=last_llm_call` to `assert_dataset_pass` in `tests/test_qa.py`.

### How to Re-Run
```bash
cd /home/yiouli/repo/pixie-qa/.claude/skills/eval-driven-dev-workspace/iteration-4/eval-debug-failures/with_skill/project && PYTHONPATH=/home/yiouli/repo/pixie-qa pixie-test tests/test_qa.py -v
```
