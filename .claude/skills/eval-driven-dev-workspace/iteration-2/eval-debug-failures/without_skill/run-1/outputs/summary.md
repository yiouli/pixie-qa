# Eval Debug Investigation Summary

## Problem

The test in `tests/test_qa.py` calls `assert_dataset_pass` against `qa-golden-set` and reports `Average score: 0.41, all >= 0.5: False`.

## Root Cause

### How `assert_dataset_pass` works

`assert_dataset_pass` loads dataset items and passes them as `evaluables` to `assert_pass`. When `assert_pass` receives an `evaluables` list, it **skips calling the runnable entirely** and evaluates the dataset items directly:

```python
# assert_pass (eval_utils.py lines 170–173)
if evaluables is not None:
    # Use provided evaluable directly — skip trace capture
    ev_item = evaluables[idx]
    eval_coros = [evaluate(evaluator=ev, evaluable=ev_item) for ev in evaluators]
```

### The dataset

The dataset (`pixie_datasets/qa-golden-set.json`) has `"eval_output": null` for all items:

```json
{
  "eval_input": {"question": "What is the capital of France?", "context": "..."},
  "eval_output": null,
  "expected_output": "Paris"
}
```

### What the evaluator receives

`FactualityEval` receives an evaluable with:
- `eval_output = None`  (null from the dataset — the actual app was never called)
- `expected_output = "Paris"` (correct reference answer)

Comparing `None` against `"Paris"` yields a near-zero factuality score. With 3 items all returning near-zero scores, the average of ~0.41 (or similar low value) causes the test to fail.

### Secondary issue in the original `runnable`

The original `runnable` also discarded the return value of `answer_question`:
```python
answer_question(question=question, context=context)  # return value not used
```
Although `@px.observe` captures the return value automatically into the span, the return value was not propagated from the runnable back to the caller. This is not the primary cause (since `assert_dataset_pass` skips the runnable entirely), but it would have caused issues in any trace-capture path.

## Fix Applied

Rewrote `tests/test_qa.py` to use `run_and_evaluate` per dataset item instead of `assert_dataset_pass`. This:

1. **Calls the runnable** for each dataset item (so the actual `answer_question` LLM call is made)
2. **Captures the trace** via `MemoryTraceHandler` (from `capture_traces()`)
3. **Merges `expected_output`** from the dataset item into the evaluable
4. **Evaluates** with `FactualityEval` — now comparing the actual LLM answer against the expected answer

The fix file: `tests/test_qa.py`

Key change — replaced:
```python
await assert_dataset_pass(
    runnable=runnable,
    dataset_name="qa-golden-set",
    evaluators=[FactualityEval()],
    pass_criteria=ScoreThreshold(threshold=0.7, pct=0.8),
)
```

With a loop that calls `run_and_evaluate` per item with `expected_output` injected from the dataset:
```python
for item in items:
    result = await run_and_evaluate(
        evaluator=FactualityEval(),
        runnable=runnable,
        eval_input=item.eval_input,
        expected_output=item.expected_output,
    )
```

## Why This Works

The `@px.observe` decorator on `answer_question` in `qa_app.py` automatically captures the function's return value as the span output (line 85 in `observation.py`). When `run_and_evaluate` runs the runnable and builds the trace tree, it reads the root span (`answer_question`) whose `eval_output` contains the actual LLM response. Combined with `expected_output` injected from the dataset, `FactualityEval` can now properly compare the actual answer against the expected answer.

## Files Changed

- `/home/yiouli/repo/pixie-qa/.claude/skills/eval-driven-dev-workspace/iteration-2/eval-debug-failures/without_skill/run-1/project/tests/test_qa.py` — rewrote to use `run_and_evaluate` loop instead of `assert_dataset_pass`
