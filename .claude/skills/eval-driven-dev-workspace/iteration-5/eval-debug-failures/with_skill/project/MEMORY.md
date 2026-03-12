## Project: QA App Eval Debug

### Entry point
`answer_question(question, context)` in `qa_app.py`.
Main entry: `main(question, context)` which calls `enable_storage()` then `answer_question(...)`.

### Instrumented spans
- `answer_question(question, context)` — `@px.observe(name="answer_question")` wraps the full pipeline
  - eval_input: `{"question": str, "context": str}`
  - eval_output: str (the answer)
  - Internally makes one Anthropic LLM call (captured as an `LLMSpan`)

### Datasets
- `qa-golden-set` (in `pixie_datasets/qa-golden-set.json`): 3 items, factual QA
  - Each item has `eval_input`, `eval_output: null`, `expected_output`
  - Examples: capital of France, author of Romeo and Juliet, boiling point of water

### Eval plan
- Evaluator: `FactualityEval`
- Pass criteria: `ScoreThreshold(threshold=0.7, pct=0.8)`
- Test file: `tests/test_qa.py::test_factuality`

### Root cause of failures (all cases scoring 0)

`assert_dataset_pass` passes `evaluables=items` to `assert_pass`. When `evaluables`
is provided, `assert_pass` takes a shortcut: it calls `evaluate(evaluable=ev_item)`
directly, **skipping the runnable entirely** and **skipping trace capture**.

Because all dataset items have `eval_output: null`, `FactualityEval` receives `None`
as the output and scores 0 on every case. The app was never actually called.

### Fix applied

Replaced `assert_dataset_pass` with a manual loop using `run_and_evaluate` per item:

1. Load dataset items manually via `DatasetStore(dataset_dir=...)`.
2. For each item, call `run_and_evaluate(runnable, eval_input, expected_output=item.expected_output, from_trace=last_llm_call)`.
   - This captures a live trace, selects the last LLM span (which has the real answer), and passes `expected_output` for `FactualityEval` to compare against.
3. Accumulate results into the `[passes][inputs][evaluators]` tensor that `ScoreThreshold` expects.
4. Call `criteria(all_evals)` and assert.

### Known issues / findings
- The dataset was pre-built with `eval_output: null` intentionally (outputs come from live runs).
- `assert_dataset_pass` is designed for replaying stored outputs, not capturing new ones. When a dataset has null outputs, you need to use `run_and_evaluate` directly.
- `from_trace=last_llm_call` selects the LLM span's text output, which is the actual answer string suitable for `FactualityEval`.

### To run tests
```bash
cd <project_dir>
PYTHONPATH=/home/yiouli/repo/pixie-qa pixie-test tests/test_qa.py -v
```
