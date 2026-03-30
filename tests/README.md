# Tests

This directory contains all tests for the pixie-qa project: automated unit tests,
automated e2e tests, and manual testing fixtures for visual inspection.

## Quick Reference

```bash
# Run all automated tests
uv run pytest

# Run only pixie module unit tests
uv run pytest tests/pixie/

# Run e2e tests for `pixie test` CLI
uv run pytest tests/pixie/cli/test_e2e_pixie_test.py -v

# Run a specific test file
uv run pytest tests/pixie/evals/test_scorecard.py -v

# Run tests matching a name pattern
uv run pytest -k "test_factuality"

# Run with coverage
uv run pytest --cov=pixie
```

## Directory Structure

```text
tests/
├── README.md                          # ← you are here
├── __init__.py
├── pixie/                             # Automated tests (pytest)
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_init.py
│   ├── cli/
│   │   ├── e2e_cases.json             # Edge-case scenarios for pixie test
│   │   ├── test_e2e_pixie_test.py     # 43 e2e tests (11 realistic + 32 edge)
│   │   ├── test_test_command.py       # pixie test config wiring
│   │   └── e2e_fixtures/
│   │       ├── test_customer_faq.py   # Realistic 4-test fixture
│   │       ├── mock_evaluators.py     # Deterministic mock evaluators
│   │       ├── conftest.py
│   │       └── datasets/
│   │           └── customer-faq.json  # 5-item golden dataset
│   ├── dataset/
│   ├── evals/
│   │   ├── test_scorecard.py          # 31 scorecard unit tests
│   │   └── ...
│   ├── instrumentation/
│   └── observation_store/
└── manual/                            # Manual testing fixtures
    ├── test_sample.py                 # 3-test sample (run with pixie test)
    ├── mock_evaluators.py             # Simple deterministic evaluators
    └── datasets/
        └── sample-qa.json            # 5-item sample dataset
```

## Manual Testing — Viewing the Scorecard

To visually inspect the HTML scorecard report, run the manual fixture:

```bash
export PIXIE_ROOT=/tmp/pixie_manual
uv run pixie test tests/manual/test_sample.py
```

`pixie test` reads the central Pixie config, so evaluator rate limits can also be supplied in a local `.env` file:

```bash
cat > .env <<'EOF'
PIXIE_RATE_LIMIT_ENABLED=true
PIXIE_RATE_LIMIT_RPS=4
PIXIE_RATE_LIMIT_RPM=50
EOF
uv run pixie test tests/manual/test_sample.py
```

This produces:

- **Console output** — 1 passed, 2 failed with ✓/✗ marks
- **HTML scorecard** — saved to `$PIXIE_ROOT/scorecards/<timestamp>.html`

Open the HTML file in a browser to inspect the scorecard:

```bash
# macOS
open /tmp/pixie_manual/scorecards/*.html

# Linux
xdg-open /tmp/pixie_manual/scorecards/*.html
```

The scorecard shows:

- Test run overview with pass/fail summary
- Per-test detail cards with scoring strategies
- Per-input × per-evaluator score grids
- Click any score to see evaluation detail (reasoning, input/output)
- Feedback modal and GitHub star CTA

### What to look for

| Test                       | Expected | Why                                                                         |
| -------------------------- | -------- | --------------------------------------------------------------------------- |
| `test_factuality`          | PASS     | Lenient threshold (0.5 score, 80% items)                                    |
| `test_keyword_coverage`    | FAIL     | Strict threshold (0.9 score, all items) — some items use different phrasing |
| `test_combined_evaluators` | FAIL     | Both evaluators must score ≥0.7 on all items                                |

### Customising the fixture

- Edit `tests/manual/datasets/sample-qa.json` to change test data
- Edit `tests/manual/mock_evaluators.py` to change scoring heuristics
- Edit `tests/manual/test_sample.py` to change evaluators or thresholds

## Automated E2E Tests

The `tests/pixie/cli/test_e2e_pixie_test.py` file contains 43 automated tests
split into two classes:

### TestPixieTestRealisticE2E (11 tests)

Runs `pixie test` on a realistic fixture with 4 evaluator/criteria combinations
against a 5-item customer-FAQ dataset. Verifies:

- Exit codes, console output, test names, ✓/✗ marks
- Scorecard HTML generation
- Evaluator names, PASS/FAIL badges, per-input scores
- Summary counts, scoring strategy descriptions
- Branding and feedback elements

### TestPixieTestEdgeCases (32 tests)

Parametrised from `e2e_cases.json`. Covers empty dirs, -k filters, verbose
mode, single file targeting, error handling. Each case specifies:

- `test_files` — inline Python test file contents
- `argv` — CLI arguments
- `expected_exit_code`
- `console_contains` / `console_not_contains`
- `scorecard_html_contains`

To add new edge cases, add entries to `e2e_cases.json` — no code changes needed.

## Unit Tests

Unit tests are in `tests/pixie/` and mirror the source structure. Key test files:

| Test file                           | Module tested                     | Tests                             |
| ----------------------------------- | --------------------------------- | --------------------------------- |
| `cli/test_test_command.py`          | `pixie.cli.test_command`          | dotenv/config wiring              |
| `evals/test_scorecard.py`           | `pixie.evals.scorecard`           | 31                                |
| `evals/test_eval_utils.py`          | `pixie.evals.eval_utils`          | assert_pass / assert_dataset_pass |
| `instrumentation/test_spans.py`     | `pixie.instrumentation.spans`     | Span data models                  |
| `instrumentation/test_processor.py` | `pixie.instrumentation.processor` | OTel processor                    |
| `instrumentation/test_queue.py`     | `pixie.instrumentation.queue`     | Delivery queue                    |

## Pre-Commit Checklist

Before committing, run:

```bash
uv run pytest                    # All tests must pass
uv run mypy pixie/               # Zero type errors
uv run ruff check .              # No linting errors
```

If you changed `pixie test`, scorecard, runner, or eval code, also run:

```bash
uv run pytest tests/pixie/cli/test_e2e_pixie_test.py -v   # 43 e2e tests
```

For scorecard visual changes, also do a manual inspection:

```bash
export PIXIE_ROOT=/tmp/pixie_verify
uv run pixie test tests/manual/test_sample.py
# Open the generated HTML and inspect visually
```
