# Expected Output in Eval Signatures

## What changed

Added an optional `expected_output` parameter to the evaluation function chain so users can supply expected values directly in their eval tests rather than only through evaluator constructors or evaluable metadata.

### New parameters

| Function                      | Parameter          | Type                | Default |
| ----------------------------- | ------------------ | ------------------- | ------- |
| `evaluate()`                  | `expected_output`  | `Any`               | `None`  |
| `run_and_evaluate()`          | `expected_output`  | `Any`               | `None`  |
| `assert_pass()`               | `expected_outputs` | `list[Any] \| None` | `None`  |
| `AutoevalsAdapter.__call__()` | `expected_output`  | `Any`               | `None`  |

### Behavior

- `evaluate()` forwards `expected_output` to the evaluator only when non-`None` (backward-compatible — existing evaluators without the parameter continue to work).
- `run_and_evaluate()` forwards `expected_output` to `evaluate()`.
- `assert_pass()` accepts `expected_outputs` (a list matching `inputs` length) and zips each value with its corresponding input. Raises `ValueError` on length mismatch.
- `AutoevalsAdapter.__call__()` integrates `expected_output` as the highest-priority expected value: call-time > constructor > metadata.

### Evaluator protocol

The `Evaluator` protocol now includes `expected_output: Any = None` in its `__call__` signature. This is backward-compatible since `evaluate()` only passes the kwarg when non-None.

## Files affected

- `pixie/evals/evaluation.py` — `Evaluator` protocol and `evaluate()` signature
- `pixie/evals/eval_utils.py` — `run_and_evaluate()` and `assert_pass()` signatures
- `pixie/evals/scorers.py` — `AutoevalsAdapter.__call__()` signature and resolution logic
- `tests/pixie/evals/test_evaluation.py` — 3 new tests
- `tests/pixie/evals/test_eval_utils.py` — 6 new tests (2 for `run_and_evaluate`, 4 for `assert_pass`)
- `tests/pixie/evals/test_scorers.py` — 3 new tests for call-time expected priority
- `specs/evals-harness.md` — updated function signatures
- `specs/autoevals-adapters.md` — updated `__call__` section
- `specs/expected-output-in-evals.md` — new implementation spec
- `README.md` — updated API reference and example

## Migration notes

No breaking changes. All new parameters default to `None`, preserving existing behavior. Existing evaluator callables that do not accept `expected_output` continue to work because `evaluate()` only forwards the kwarg when it is non-`None`.
