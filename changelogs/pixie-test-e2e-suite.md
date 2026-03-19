# pixie test — e2e test suite

## What changed

Added a comprehensive end-to-end test suite for the `pixie test` CLI command
with two complementary layers:

1. **Realistic fixture tests** (10 tests) — run `pixie test` on a realistic
   test file with a 5-item customer-FAQ golden dataset and 4 deterministic
   mock evaluators. Verifies exit code, console summary, test names,
   check/cross marks, scorecard HTML generation, evaluator names, PASS/FAIL
   badges, per-input scores, summary counts, and scoring strategy descriptions.

2. **Edge-case tests** (32 tests) — parametrised from `e2e_cases.json`
   covering empty dirs, filters, verbose mode, single file targeting, etc.

The copilot instructions now include an **agent verification protocol** that
tells the coding agent to manually run `pixie test` on the realistic fixtures
and holistically evaluate the console output and HTML scorecard after making
changes to CLI/eval/scorecard code.

### New files

- **`tests/pixie/cli/e2e_fixtures/datasets/customer-faq.json`** — 5-item
  golden dataset with FAQ questions, chatbot answers, and reference answers.

- **`tests/pixie/cli/e2e_fixtures/mock_evaluators.py`** — 4 deterministic
  mock evaluators: MockFactualityEval (SequenceMatcher string similarity),
  MockClosedQAEval (keyword overlap), MockHallucinationEval (always 0.95),
  MockFailingEval/MockStrictTone (always 0.2). No LLM calls.

- **`tests/pixie/cli/e2e_fixtures/test_customer_faq.py`** — Realistic test
  file using `assert_dataset_pass` with different scoring strategies.
  Expected: 2 PASS (`test_faq_factuality`, `test_faq_no_hallucinations`),
  2 FAIL (`test_faq_multi_evaluator`, `test_faq_tone_check`).

- **`tests/pixie/cli/e2e_cases.json`** — 8 edge-case scenarios as JSON data.

- **`tests/pixie/cli/test_e2e_pixie_test.py`** — Two test classes:
  `TestPixieTestRealisticE2E` (10 tests) and `TestPixieTestEdgeCases`
  (32 tests). Total: 42 test cases.

### Modified files

- **`.github/copilot-instructions.md`** — Rewrote section 4a with realistic
  fixture layout, mock evaluator descriptions, expected results, and a full
  agent verification protocol. Updated summary checklist to require both
  automated e2e tests (42) and manual agent inspection.

- **`specs/evals-harness.md`** — Updated E2E Test Suite section to describe
  both realistic fixtures and edge-case scenarios.

## Files affected

- `tests/pixie/cli/e2e_fixtures/datasets/customer-faq.json`
- `tests/pixie/cli/e2e_fixtures/mock_evaluators.py`
- `tests/pixie/cli/e2e_fixtures/test_customer_faq.py`
- `tests/pixie/cli/e2e_cases.json`
- `tests/pixie/cli/test_e2e_pixie_test.py`
- `.github/copilot-instructions.md`
- `specs/evals-harness.md`

## Migration notes

No API changes. The e2e test suite is purely additive.

- To add new edge-case scenarios: edit `tests/pixie/cli/e2e_cases.json`.
- To modify realistic fixture behavior: edit mock evaluators or the test file
  in `tests/pixie/cli/e2e_fixtures/`.
