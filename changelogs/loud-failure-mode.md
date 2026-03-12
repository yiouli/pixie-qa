# Loud Failure Mode

## What Changed

Eliminated all silent failure paths in the eval harness. Runtime errors (missing
API keys, import failures, evaluator crashes) now propagate as exceptions instead
of being silently swallowed.

### 1. `evaluate()` — evaluator exceptions propagate

**Before:** Any exception from an evaluator (e.g. missing API key, network error)
was caught and returned as `Evaluation(score=0.0, reasoning=str(exc))`. This made
real errors indistinguishable from legitimate low scores.

**After:** Evaluator exceptions propagate unchanged to the caller. If an evaluator
cannot run, the test fails loudly with the original error and traceback.

### 2. `_load_module()` / `discover_tests()` — import errors propagate

**Before:** `_load_module()` caught all exceptions and returned `None`, causing
`discover_tests()` to silently skip broken test files. The result was
"no tests collected" with no explanation.

**After:** Import errors (missing packages, syntax errors, bad imports) propagate
immediately with the original traceback, making the root cause obvious.

### 3. `format_results()` — error messages always visible

**Before:** Failure and error messages were only shown with `--verbose` flag.
Without it, tests showed only `✗` with no message.

**After:** The first line of the error message is always shown. `--verbose`
controls whether the full traceback is displayed.

### 4. Removed dead `evals/` resource folder

Deleted `.claude/skills/eval-driven-dev/evals/` (contained `evals.json` and
`sample-projects/` with no references from the skill instructions).

## Files Affected

- `pixie/evals/evaluation.py` — removed exception swallowing in `evaluate()`
- `pixie/evals/runner.py` — `_load_module()` raises on error; `discover_tests()`
  propagates; `format_results()` always shows messages
- `tests/pixie/evals/test_evaluation.py` — updated test: expects propagation
  instead of `score=0.0`; added sync evaluator error test
- `tests/pixie/evals/test_runner.py` — added import error, syntax error,
  and format_results tests
- `specs/evals-harness.md` — updated error handling behavior and test expectations
- `.claude/skills/eval-driven-dev/evals/` — deleted

## Migration Notes

- `evaluate()` no longer catches evaluator exceptions. Code that relied on
  getting `Evaluation(score=0.0, details={"error": ...})` from crashed evaluators
  must now handle exceptions directly.
- `discover_tests()` now raises on import errors instead of silently skipping
  broken test files.
