# Single Runnable Execution Per Input

## What Changed

Fixed a bug where `_process_single_input` called the runnable once per evaluator
instead of once per input. With N evaluators, the runnable was invoked N times
for the same input — redundant, wasteful, and potentially unsafe for apps with
shared mutable state.

**Before:** 3 evaluators × 5 inputs = 15 runnable calls.
**After:** 3 evaluators × 5 inputs = 5 runnable calls (one per input, shared
across evaluators).

### Refactoring

Extracted `_run_and_capture()` — a private helper that runs the runnable once,
captures traces, builds the tree, and returns `(Evaluable, trace_tree)`. Both
`run_and_evaluate()` and `_process_single_input()` now use this helper.

`run_and_evaluate()` is unchanged in its public API — it still runs exactly once
and returns a single `Evaluation`.

## Files Affected

- `pixie/evals/eval_utils.py` — added `_run_and_capture()`, refactored
  `run_and_evaluate()` and `_process_single_input()`
- `tests/pixie/evals/test_eval_utils.py` — added 3 new tests:
  `test_runnable_called_once_per_input_with_multiple_evaluators`,
  `test_runnable_once_without_evaluables`,
  `test_all_evaluators_see_same_output`

## Migration Notes

No API changes. `run_and_evaluate` and `assert_pass` behave identically from
the caller's perspective. Internal-only refactor.
