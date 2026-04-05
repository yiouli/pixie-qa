# Step 6: Run Evaluation-Based Tests

**Why this step**: With the dataset ready (including runnable, evaluators, and items), you run `pixie test` to execute the full evaluation pipeline and verify that real scores are produced.

---

## 6a. Run tests

Run with `pixie test` (not `pytest`). No path argument is needed — `pixie test` automatically discovers and runs all dataset JSON files in the pixie datasets directory:

```bash
uv run pixie test
```

For verbose output showing per-case scores and evaluator reasoning:

```bash
uv run pixie test -v
```

`pixie test` automatically loads the `.env` file before running tests, so API keys do not need to be exported in the shell.

## 6b. Verify test output

After running, verify:

1. Per-entry results appear with evaluator names and real scores
2. No import errors, missing key errors, or other setup failures
3. Per-evaluator scores appear with real values (not all zeros or all ones)

**If the test errors out** (import failures, missing keys, runnable resolution errors), that's a setup bug — fix the dataset JSON, the runnable function, or the evaluator implementations and re-run. Common issues:

| Error                            | Likely cause                                                                   | Fix                                                            |
| -------------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------- |
| Runnable resolution failure      | `runnable` in dataset doesn't point to a valid function                        | Fix the `filepath:callable_name` reference in the dataset JSON |
| Evaluator resolution failure     | Evaluator name doesn't match built-in names or `filepath:callable_name` format | Check evaluator names in `evaluators.md` reference             |
| Eval_input shape mismatch        | Dataset eval_input fields don't match what the runnable expects                | Match field names/types from the reference trace               |
| Import error in custom evaluator | Module path wrong or syntax error                                              | Fix the evaluator module                                       |
| `ModuleNotFoundError: pixie_qa`  | `pixie_qa/` directory missing `__init__.py`                                    | Run `pixie init` again (it creates `__init__.py`)              |
| `TypeError: ... is not callable` | Evaluator name points to a non-callable attribute                              | Evaluators must be functions, classes, or callable instances   |

**If the test produces real pass/fail scores**, that's the deliverable — proceed to analysis.

## 6c. Run analysis

Once tests complete without errors caused by problems with dataset values or run-harness implementation issues, run analysis:

```bash
uv run pixie analyze <test_id>
```

Where `<test_id>` is the test run identifier printed by `pixie test` (e.g., `20250615-120000`). This generates LLM-powered markdown analysis for each dataset, identifying patterns in successes and failures.

## Output

- Test results at `{PIXIE_ROOT}/results/<test_id>/result.json`
- Analysis files at `{PIXIE_ROOT}/results/<test_id>/dataset-<index>.md` (after `pixie analyze`)

---

> **If you hit an unexpected error** when running tests (wrong parameter names, import failures, API mismatch), read the relevant reference file (`evaluators.md`, `instrumentation-api.md`, or `testing-api.md`) for the authoritative API reference before guessing at a fix.
