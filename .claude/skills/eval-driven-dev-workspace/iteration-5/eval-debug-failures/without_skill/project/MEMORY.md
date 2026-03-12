# Eval Test Debugging — MEMORY

## Root Cause Analysis

The eval tests in `tests/test_qa.py` were scoring 0 for all test cases due to two bugs.

### Bug 1: `runnable` did not return the answer

In the original `test_qa.py`, the `runnable` function called `answer_question(...)` but did not `return` its result:

```python
# BROKEN
def runnable(eval_input):
    enable_storage()
    ...
    answer_question(question=question, context=context)  # return value discarded
```

This meant the actual LLM output was never captured as the `eval_output` for evaluation.

### Bug 2: `assert_dataset_pass` bypasses the runnable entirely

`assert_dataset_pass` loads dataset items and passes them as `evaluables` to `assert_pass`. When `evaluables` is provided to `assert_pass`, it skips trace capture and the runnable altogether — it evaluates the static `eval_output` from the dataset items directly.

Since the dataset JSON (`pixie_datasets/qa-golden-set.json`) has `"eval_output": null` for all items, every call to `FactualityEval` received `output=None` and scored 0.

The chain:
1. `assert_dataset_pass` → loads items with `eval_output=null` → passes as `evaluables`
2. `assert_pass` with `evaluables` provided → skips runnable, evaluates static items
3. Evaluator sees `output=None`, `expected="Paris"` → score = 0

## Fix Applied

Rewrote `tests/test_qa.py` to:

1. **Return the answer in `runnable`** — added `return` to capture live LLM output.
2. **Manually populate `eval_output`** before evaluation — load the dataset, run the runnable for each item via `asyncio.to_thread`, build a new `Evaluable` with the live output and the dataset's `expected_output`.
3. **Use `assert_pass` with populated evaluables** — passes evaluables that have both `eval_output` (live LLM answer) and `expected_output` (ground truth from dataset).

## Key Framework Behavior Notes

- `assert_dataset_pass(runnable, dataset_name, evaluators)` loads a dataset and passes items as static `evaluables` to `assert_pass`. The runnable is **NOT** called.
- `assert_pass(runnable, eval_inputs, evaluators, evaluables=None)`: when `evaluables` is provided, the runnable is skipped; when `evaluables=None`, trace capture is used but `expected_output` is not injected per item.
- For live evaluation against a golden dataset, the test must manually run the runnable, capture outputs, and construct `Evaluable` objects with both `eval_output` and `expected_output` before calling `assert_pass`.

## Files Modified

- `tests/test_qa.py` — fixed `runnable` return value and rewrote `test_factuality` to populate evaluables with live LLM output before evaluation.
