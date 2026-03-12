# Investigating and Fixing pixie-test Failures in qa-golden-set

## Understanding the Error Message

The message `Average score: 0.41, all >= 0.5: False` comes from the default pass criteria in `pixie/evals/eval_utils.py`. When no custom `pass_criteria` is supplied to `assert_pass` or `assert_dataset_pass`, the default function `_default_pass_criteria` is used, which requires every individual score to be >= 0.5 and reports the average.

This message alone tells you that some cases scored below 0.5, but it does not tell you which ones or why.

## Step 1: Re-run with Verbose Mode

The simplest first step is to re-run the tests with the `-v` flag:

```bash
pixie-test -v
```

Or if running against a specific file or filter:

```bash
pixie-test tests/ -k qa-golden-set -v
```

The `-v` flag causes `format_results` in `runner.py` to print the full failure message for each failed test, which includes the `EvalAssertionError` message.

## Step 2: Access the Full Results Tensor from EvalAssertionError

The `EvalAssertionError` (a subclass of `AssertionError`) carries the full results tensor as `err.results`. This tensor has shape `[passes][inputs][evaluators]` where each cell is an `Evaluation(score, reasoning, details)` object.

To inspect it directly, add a try/except block in your test file temporarily:

```python
from pixie.evals import assert_dataset_pass, EvalAssertionError

async def test_qa_golden_set():
    try:
        await assert_dataset_pass(
            runnable=my_qa_app,
            dataset_name="qa-golden-set",
            evaluators=[my_evaluator],
        )
    except EvalAssertionError as e:
        # e.results shape: [passes][inputs][evaluators]
        for pass_idx, pass_results in enumerate(e.results):
            for input_idx, input_evals in enumerate(pass_results):
                for eval_idx, ev in enumerate(input_evals):
                    if ev.score < 0.5:
                        print(
                            f"FAIL pass={pass_idx} input={input_idx} eval={eval_idx}: "
                            f"score={ev.score:.2f} reasoning={ev.reasoning!r} "
                            f"details={ev.details}"
                        )
        raise
```

This will print every failing case with its score, reasoning (the evaluator's human-readable explanation), and any extra details.

## Step 3: Correlate Inputs to Their Indices

The results tensor is indexed the same way as your dataset items. Load the dataset explicitly to map indices back to inputs:

```python
from pixie.dataset import DatasetStore

store = DatasetStore()
ds = store.get("qa-golden-set")
items = list(ds.items)

# Now items[input_idx] corresponds to results[pass_idx][input_idx]
for input_idx, item in enumerate(items):
    print(f"[{input_idx}] input={item.eval_input!r} expected={item.expected_output!r}")
```

Combine this with the loop above to print the actual input, expected output, and what your app produced (`evaluable.eval_output`) alongside the score.

## Step 4: Inspect What the App Is Actually Returning

If the evaluator's `reasoning` field is not enough, you need to see what `eval_output` your app produced. The `Evaluable` is built from the captured trace — specifically from the root observation span's output (or the LLM span's output if you used `from_trace=last_llm_call`).

Add a custom evaluator or logging evaluator temporarily:

```python
from pixie.evals import Evaluation
from pixie.storage.evaluable import Evaluable

async def debug_evaluator(evaluable: Evaluable, *, trace=None) -> Evaluation:
    print(f"INPUT:    {evaluable.eval_input!r}")
    print(f"OUTPUT:   {evaluable.eval_output!r}")
    print(f"EXPECTED: {evaluable.expected_output!r}")
    # Always pass so this doesn't interfere
    return Evaluation(score=1.0, reasoning="debug")
```

Then add it to your evaluators list alongside your real evaluator during debugging.

## Step 5: Check for Evaluator Errors

A score of 0.0 can also mean the evaluator itself threw an exception. In that case, `evaluate()` catches the error and returns `Evaluation(score=0.0, reasoning=<exception message>, details={"error": ..., "traceback": ...})`.

Check the `details` field of any zero-scored results:

```python
if ev.score == 0.0 and ev.details.get("error"):
    print(f"Evaluator raised {ev.details['error']}: {ev.reasoning}")
    print(ev.details.get("traceback", ""))
```

Common causes:
- LLM-as-judge evaluator failing due to missing API key or quota
- `expected_output` is `UNSET` when the evaluator requires it
- Network timeout or rate limit

## Step 6: Check the Dataset Itself

If the expected outputs in your dataset are stale or wrong, even correct app outputs will fail. Inspect the dataset file:

```bash
pixie dataset list
```

The dataset JSON files live in the directory configured by `PIXIE_DATASET_DIR` (default: `pixie_datasets/`). Open `pixie_datasets/qa-golden-set.json` directly to review all items, their `eval_input`, `expected_output`, and any `eval_metadata`.

If an item has an incorrect or outdated `expected_output`, update the dataset:

```python
store = DatasetStore()
ds = store.get("qa-golden-set")
# Inspect items
for i, item in enumerate(ds.items):
    print(i, item)

# Remove a bad item and re-add with correct expected output
store.remove("qa-golden-set", index=2)
store.append("qa-golden-set", Evaluable(
    eval_input="...",
    expected_output="...",
))
```

Or capture a fresh golden trace:

```bash
# Run your app once on the correct input, then save to the dataset
pixie dataset save qa-golden-set --notes "refreshed golden"
echo '"correct expected output"' | pixie dataset save qa-golden-set --expected-output
```

## Step 7: Fix the Failures

Once you know which cases are failing and why, the fix will be one of:

1. **App regression** — the app's output changed. Fix the application logic, then re-run `pixie-test`.

2. **Stale expected output** — the expected output in the dataset no longer matches acceptable app behavior. Refresh the dataset items (Step 6).

3. **Evaluator misconfiguration** — the evaluator's threshold, model, or expected value is wrong. Adjust the evaluator arguments or switch to a more appropriate evaluator type.

4. **Evaluator error** — missing API key, network issue, etc. Fix the environment (e.g., set `OPENAI_API_KEY`) and re-run.

5. **Flaky LLM judge** — if using an LLM-as-judge evaluator, scores can vary. Use `passes=3` or a `ScoreThreshold(threshold=0.5, pct=0.8)` to tolerate occasional borderline outputs:

```python
from pixie.evals import assert_dataset_pass, ScoreThreshold

await assert_dataset_pass(
    runnable=my_qa_app,
    dataset_name="qa-golden-set",
    evaluators=[my_evaluator],
    passes=3,
    pass_criteria=ScoreThreshold(threshold=0.5, pct=0.8),
)
```

## Summary: Recommended Debug Sequence

1. `pixie-test -v` for quick verbose output
2. Wrap in try/except to print per-case `score`, `reasoning`, and `details` from the `EvalAssertionError.results` tensor
3. Map `input_idx` back to dataset items via `DatasetStore.get("qa-golden-set")`
4. Add a `debug_evaluator` to log `eval_input` / `eval_output` / `expected_output` for failing cases
5. Check for evaluator errors (score=0.0 with `details["error"]`)
6. Fix app, dataset, or evaluator config as appropriate
