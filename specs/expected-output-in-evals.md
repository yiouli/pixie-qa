# Expected Output in Eval Signatures — Implementation Spec

## Overview

Add an optional `expected_output` parameter to the pixie evaluation function signatures so users can supply expected values directly in their eval tests rather than embedding them only inside evaluator constructors or evaluable metadata.

This is the natural place for expected outputs in a test harness:

```python
await assert_pass(
    runnable=my_qa_app,
    inputs=["What is 2+2?", "Capital of France?"],
    expected_outputs=["4", "Paris"],
    evaluators=[FactualityEval()],
)
```

---

## Motivation

Currently, expected values can only be provided in two ways:

1. **Fixed at evaluator construction time** — `FactualityEval(expected="Paris")`. This limits a single evaluator instance to a single expected value, so users must create separate evaluator instances per test case.
2. **Via evaluable metadata** — `evaluable.eval_metadata["expected"]`. This requires the underlying span to happen to carry the expected value in its metadata, which is unreliable for test-time expectations.

Neither is ergonomic for the common case: a batch of `(input, expected_output)` pairs evaluated by the same set of evaluators.

---

## Changes

### 1. `Evaluator` protocol

Add `expected_output` as an optional keyword argument:

```python
class Evaluator(Protocol):
    async def __call__(
        self,
        evaluable: Evaluable,
        *,
        expected_output: Any = None,
        trace: list[ObservationNode] | None = None,
    ) -> Evaluation: ...
```

This is backward-compatible: existing evaluators that don't declare `expected_output` in their signature still satisfy the protocol because Python callables accept extra `**kwargs` and `evaluate()` catches `TypeError` / forwards via `**kwargs` semantics. In practice `evaluate()` always passes the kwarg if it is not `None`.

### 2. `evaluate()`

```python
async def evaluate(
    evaluator: Callable[..., Any],
    evaluable: Evaluable,
    *,
    expected_output: Any = None,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
```

Behavior change: passes `expected_output=expected_output` to the evaluator call when `expected_output` is not `None`.

### 3. `run_and_evaluate()`

```python
async def run_and_evaluate(
    evaluator: Callable[..., Any],
    runnable: Callable[..., Any],
    input: Any,
    *,
    expected_output: Any = None,
    from_trace: Callable[[list[ObservationNode]], Evaluable] | None = None,
) -> Evaluation:
```

Forwards `expected_output` to `evaluate()`.

### 4. `assert_pass()`

```python
async def assert_pass(
    runnable: Callable[..., Any],
    inputs: list[Any],
    evaluators: list[Callable[..., Any]],
    *,
    expected_outputs: list[Any] | None = None,
    passes: int = 1,
    pass_criteria: ... = None,
    from_trace: ... = None,
) -> None:
```

- `expected_outputs` is an optional list the same length as `inputs`.
- When provided, `expected_outputs[i]` is forwarded as `expected_output` to `run_and_evaluate` for input `i`.
- When omitted or `None`, `expected_output=None` is forwarded (preserving current behavior).
- Raises `ValueError` if `expected_outputs` is not `None` and `len(expected_outputs) != len(inputs)`.

### 5. `AutoevalsAdapter.__call__`

```python
async def __call__(
    self,
    evaluable: Evaluable,
    *,
    expected_output: Any = None,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
```

Expected-value resolution priority (highest to lowest):

1. `expected_output` passed at call time (from `evaluate()`)
2. Constructor-provided `expected` (from factory function)
3. `evaluable.eval_metadata[expected_key]`

---

## Files affected

| File                                   | Change                                                                                             |
| -------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `pixie/evals/evaluation.py`            | `Evaluator` protocol: add `expected_output` kwarg; `evaluate()`: add and forward `expected_output` |
| `pixie/evals/eval_utils.py`            | `run_and_evaluate()`: add `expected_output`; `assert_pass()`: add `expected_outputs`               |
| `pixie/evals/scorers.py`               | `AutoevalsAdapter.__call__`: accept `expected_output`, integrate into resolution priority          |
| `tests/pixie/evals/test_evaluation.py` | Tests for `expected_output` passthrough in `evaluate()`                                            |
| `tests/pixie/evals/test_eval_utils.py` | Tests for `expected_output` / `expected_outputs` in utils                                          |
| `tests/pixie/evals/test_scorers.py`    | Tests for `expected_output` override in adapter                                                    |
| `specs/evals-harness.md`               | Update evaluate / run_and_evaluate / assert_pass signatures                                        |
| `specs/autoevals-adapters.md`          | Update AutoevalsAdapter.**call** section                                                           |

---

## Backward compatibility

All new parameters default to `None`, so every existing evaluator, test, and call site continues to work without changes.
