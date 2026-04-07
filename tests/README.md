# Tests

This directory contains all tests for the pixie-qa project: automated unit tests,
automated e2e tests, and manual testing fixtures for visual inspection.

## Quick Reference

```bash
# Run all automated tests
uv run pytest

# Run only pixie module unit tests
uv run pytest tests/pixie/

# Run a specific test file
uv run pytest tests/pixie/eval/test_scorers.py -v

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
│   ├── test_config_tracing.py
│   ├── test_init.py
│   ├── cli/
│   │   ├── test_test_command.py       # pixie test config wiring
│   │   ├── test_analyze_command.py    # pixie analyze CLI tests
│   │   ├── test_init_command.py       # pixie init CLI tests
│   │   ├── test_main.py              # CLI main entry point tests
│   │   ├── test_trace_format_commands.py  # pixie trace / pixie format tests
│   │   └── e2e_fixtures/
│   │       ├── mock_evaluators.py     # Deterministic mock evaluators
│   │       ├── conftest.py
│   │       └── datasets/
│   │           └── customer-faq.json  # 5-item golden dataset with evaluators per row
│   ├── eval/
│   │   ├── test_dataset_runner.py     # Dataset loading and runner tests
│   │   ├── test_evaluation.py         # Evaluator protocol and evaluate() tests
│   │   ├── test_llm_evaluator.py      # create_llm_evaluator tests
│   │   ├── test_rate_limiter.py       # Rate limiter tests
│   │   ├── test_runnable.py           # Runnable protocol tests
│   │   ├── test_scorers.py            # Autoevals adapter tests
│   │   └── test_test_result.py        # Test result JSON model tests
│   ├── instrumentation/
│   │   ├── test_handler.py            # Handler registry tests
│   │   ├── test_processor.py          # OTel LLMSpanProcessor tests
│   │   ├── test_queue.py              # Delivery queue tests
│   │   ├── test_spans.py              # Span data model tests
│   │   ├── test_wrap.py               # wrap() API tests
│   │   ├── test_wrap_log.py           # Wrap log entry tests
│   │   ├── test_wrap_processors.py    # TraceLogProcessor / EvalCaptureLogProcessor tests
│   │   ├── test_wrap_registry.py      # Wrap registry tests
│   │   └── test_wrap_serialization.py # jsonpickle serialization tests
│   └── web/
│       ├── test_app.py                # Web UI server + CLI tests
│       └── test_watcher.py            # File watcher utility tests
└── manual/                            # Manual testing fixtures
    ├── mock_evaluators.py             # Simple deterministic evaluators
    └── datasets/
        └── sample-qa.json            # 5-item sample dataset with evaluators per row
```

## Manual Testing — Agent Verification Protocol

Whenever you change CLI, eval, or scorecard code, run the manual fixture and
inspect both the console output and the generated result.

### 1. Run the manual fixture

```bash
export PIXIE_ROOT=/tmp/pixie_e2e_verify
uv run pixie test tests/manual/datasets/sample-qa.json --no-open
```

### 2. Inspect console output

Verify that:

- All 5 dataset entries appear with correct ✓/✗ marks
- Evaluator names are shown per row (e.g. `(SimpleFactualityEval, StrictKeywordEval)`)
- Scores are shown (e.g. `[1.00, 1.00]`)
- The result JSON file path is printed at the end
- No unexpected errors or tracebacks

### 3. Inspect the result JSON and web UI

Write a Playwright script to:

- Open the generated HTML file via `file://` URL
- Verify evaluator names appear (SimpleFactualityEval, StrictKeywordEval)
- Verify per-input score cells show reasonable numeric values
- Verify PASS/FAIL badges are present
- Check that "details" links exist and clicking one opens the evaluation detail modal
- Take a screenshot for visual confirmation

Example:

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("file:///tmp/pixie_e2e_verify/scorecards/<filename>.html")
    page.wait_for_load_state("networkidle")

    body = page.inner_text("body")
    assert "SimpleFactualityEval" in body
    assert "StrictKeywordEval" in body
    assert "sample-qa" in body

    # Verify detail modal opens
    details = page.locator("text=details")
    assert details.count() > 0
    details.first.click()
    page.wait_for_timeout(500)
    assert "Evaluation detail" in page.inner_text("body")

    page.screenshot(path="/tmp/pixie_scorecard.png", full_page=True)
    browser.close()
```

### Customising the fixture

- Edit `tests/manual/datasets/sample-qa.json` to change test data and evaluators
- Edit `tests/manual/mock_evaluators.py` to change scoring heuristics

## Unit Tests

Unit tests are in `tests/pixie/` and mirror the source structure. Key test files:

| Test file                           | Module tested                                | Tests                             |
| ----------------------------------- | -------------------------------------------- | --------------------------------- |
| `cli/test_test_command.py`          | `pixie.cli.test_command`                     | dotenv/config wiring              |
| `cli/test_analyze_command.py`       | `pixie.cli.analyze_command`                  | pixie analyze CLI                 |
| `cli/test_init_command.py`          | `pixie.cli.init_command`                     | pixie init scaffolding            |
| `cli/test_main.py`                  | `pixie.cli.main`                             | CLI entry point                   |
| `cli/test_trace_format_commands.py` | `pixie.cli.trace_command` / `format_command` | pixie trace / format              |
| `eval/test_dataset_runner.py`       | `pixie.harness.runner`                       | Dataset loading and eval runner   |
| `eval/test_evaluation.py`           | `pixie.eval.evaluation`                      | Evaluator protocol, evaluate()    |
| `eval/test_llm_evaluator.py`        | `pixie.eval.llm_evaluator`                   | create_llm_evaluator              |
| `eval/test_rate_limiter.py`         | `pixie.eval.rate_limiter`                    | Rate limiting                     |
| `eval/test_runnable.py`             | `pixie.harness.runnable`                     | Runnable protocol                 |
| `eval/test_scorers.py`              | `pixie.eval.scorers`                         | Autoevals adapters                |
| `eval/test_test_result.py`          | `pixie.harness.run_result`                   | Test result JSON models           |
| `instrumentation/test_handler.py`   | `pixie.instrumentation.llm_tracing`          | Handler registry                  |
| `instrumentation/test_processor.py` | `pixie.instrumentation.llm_tracing`          | OTel LLMSpanProcessor             |
| `instrumentation/test_queue.py`     | `pixie.instrumentation.llm_tracing`          | Delivery queue                    |
| `instrumentation/test_spans.py`     | `pixie.instrumentation.llm_tracing`          | Span data models                  |
| `instrumentation/test_wrap.py`      | `pixie.instrumentation.wrap`                 | wrap() API                        |
| `web/test_app.py`                   | `pixie.web.app` + CLI                        | Manifest, SSE, endpoints, CLI     |
| `web/test_watcher.py`               | `pixie.web.watcher`                          | Artifact filtering, change labels |

## Pre-Commit Checklist

Before committing, run:

```bash
uv run pre-commit run --all-files  # Regenerates docs/pixie/**/*.md via pdoc3 hook
uv run pytest                    # All tests must pass
uv run mypy pixie/               # Zero type errors
uv run ruff check .              # No linting errors
```

If you changed `pixie test`, scorecard, dataset runner, or eval code, also run the
**agent verification protocol** (see Manual Testing section above) — run `pixie test`
on the manual fixture and inspect console output + scorecard HTML with Playwright.
