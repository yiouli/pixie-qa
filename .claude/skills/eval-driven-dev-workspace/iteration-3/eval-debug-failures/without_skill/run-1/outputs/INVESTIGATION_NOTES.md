# Eval Test Failure Investigation Notes

## Root Cause

The eval tests in `tests/test_qa.py` were always scoring 0 (failing) due to two compounding bugs.

### Bug 1: `assert_dataset_pass` skips the runnable when evaluables are provided

`assert_dataset_pass` loads the dataset from disk and calls:

```python
await assert_pass(
    runnable=runnable,
    eval_inputs=eval_inputs,
    evaluables=items,   # <-- dataset items passed here
    ...
)
```

Inside `assert_pass`, when `evaluables` is provided, the code path is:

```python
if evaluables is not None:
    ev_item = evaluables[idx]
    eval_coros = [evaluate(evaluator=ev, evaluable=ev_item) for ev in evaluators]
```

**The `runnable` is never called.** The evaluator receives `ev_item.eval_output` directly from the dataset JSON.

### Bug 2: All dataset items have `eval_output: null`

In `pixie_datasets/qa-golden-set.json`, every item has:

```json
"eval_output": null
```

Because `assert_dataset_pass` uses these stored evaluables directly (not live app output), `FactualityEval` always receives `output=None`, producing score 0 for every item.

### Bug 3 (secondary): `runnable` discarded return value and called `enable_storage()` per-call

The original `runnable`:
```python
def runnable(eval_input):
    enable_storage()                              # wrong: reinitializes per call
    answer_question(question=question, context=context)  # return value discarded
```

Even if trace capture had been active, `enable_storage()` would re-initialize storage on every call, and the discarded return value meant the output would never be captured.

## Fix Applied

Rewrote `tests/test_qa.py` to:

1. **Call `px.init()` once** at the start of the test.
2. **For each dataset item**, use `capture_traces()` to capture the real LLM output:
   - Run `answer_question()` inside the `capture_traces()` context
   - Extract the LLM span via `last_llm_call(trace_tree)`
   - Build an `Evaluable` with the live `eval_output` AND the `expected_output` from the dataset
3. **Pass the live evaluables** to `assert_pass` so `FactualityEval` can compare the real app output against the golden expected output.

## How to Re-run

```bash
cd /home/yiouli/repo/pixie-qa/.claude/skills/eval-driven-dev-workspace/iteration-3/eval-debug-failures/without_skill/project

# Using pixie's test runner:
PYTHONPATH=/home/yiouli/repo/pixie-qa python -m pixie test tests/test_qa.py

# Or using pytest directly (requires ANTHROPIC_API_KEY in environment):
PYTHONPATH=/home/yiouli/repo/pixie-qa pytest tests/test_qa.py -v
```

Make sure `ANTHROPIC_API_KEY` is set in the environment before running.
