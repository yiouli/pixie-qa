# Simplify eval API: remove `passes` parameter and flatten results

## What changed

Removed the multi-pass dimension from the eval system. The `passes` parameter has been removed from `assert_pass` and `assert_dataset_pass`, and the results tensor has been flattened from `[passes][inputs][evaluators]` to `[inputs][evaluators]`.

**Breaking changes:**

- `assert_pass()` and `assert_dataset_pass()` no longer accept a `passes` keyword argument.
- `EvalAssertionError.results` type changed from `list[list[list[Evaluation]]]` to `list[list[Evaluation]]`.
- `ScoreThreshold.__call__` accepts `list[list[Evaluation]]` instead of `list[list[list[Evaluation]]]`.
- Custom `pass_criteria` callables must accept `list[list[Evaluation]]` (2D: inputs × evaluators).
- `AssertRecord.results` in the scorecard changed from 3D to 2D.
- Frontend `AssertRecordData.results` changed from `EvaluationData[][][]` to `EvaluationData[][]`.
- Pass tabs removed from the scorecard UI — each assert now renders a single flat table.

## Why

The multi-pass "best-of-N" semantics added complexity without practical benefit. Most eval scenarios need: 1 dataset, 1 test function, run each input once, evaluate with each evaluator. The simplified API and scorecard are easier to understand and use.

## Files affected

### pixie-qa (package)

- `pixie/evals/criteria.py` — `ScoreThreshold.__call__` signature and logic simplified
- `pixie/evals/eval_utils.py` — removed `passes` parameter, flattened results shape
- `pixie/evals/scorecard.py` — `AssertRecord.results` type, serialization, criteria description
- `frontend/src/types.ts` — `AssertRecordData.results` type flattened
- `frontend/src/components/AssertCard.tsx` — removed pass tabs UI and `useState` import
- `pixie/assets/index.html` — rebuilt frontend
- `pixie/assets/webui.html` — rebuilt frontend
- `tests/pixie/evals/test_criteria.py` — removed multi-pass tests, updated data shapes
- `tests/pixie/evals/test_scorecard.py` — updated helper and assertions for 2D results
- `tests/pixie/evals/test_eval_utils.py` — removed `test_multiple_passes` tests, updated shape assertions
- `skills/eval-driven-dev/references/pixie-api.md` — removed `passes` from API signature

### pixie-qa-skill-development (skill v21)

- `skill_versions/v21/references/pixie-api.md` — removed `passes` from API signature

## Migration notes

- Remove any `passes=N` arguments from `assert_pass` / `assert_dataset_pass` calls.
- Update custom `pass_criteria` callables to accept `list[list[Evaluation]]` instead of `list[list[list[Evaluation]]]`.
- Update any code that accesses `EvalAssertionError.results` — remove one level of list indexing (e.g., `results[0][0][0]` → `results[0][0]`).
