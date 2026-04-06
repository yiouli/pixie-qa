# GitHub Copilot Instructions for pixie-qa

## Project Overview

pixie-qa is a Python package and coding-agent skill for automated quality assurance of AI applications. The package is published as `pixie` and provides instrumentation, evaluation, and observability primitives that plug into LLM-powered apps.

## Technology Stack

- **Python 3.11+** with type hints
- **uv** for package management, virtual environments, and builds
- **pytest** for testing
- **mypy** for static type checking
- **ruff** for linting and formatting
- **OpenTelemetry SDK** and **OpenInference** for LLM call instrumentation

## Package Structure

```
pixie/
  __init__.py
  assets/
    index.html           # compiled React scorecard (build artifact, gitignored)
  cli/
    test_command.py      # pixie test entry point
  evals/
    scorecard.py         # scorecard data models + template-based HTML generation
    dataset_runner.py    # dataset-driven test runner (evaluator resolution, discovery)
  instrumentation/
    __init__.py          # public API: init(), flush()
    spans.py             # ObserveSpan, LLMSpan, message/content types
    handler.py           # InstrumentationHandler ABC
    wrap.py              # wrap() API for data-object-based tracing
    processor.py         # LLMSpanProcessor (OTel SpanProcessor)
    queue.py             # _DeliveryQueue (background worker thread)
    instrumentors.py     # auto-discovers and activates OpenInference instrumentors
    py.typed

frontend/                # React scorecard SPA source
  src/                   # React components, types, styles
  package.json           # React 19, Vite 6, vite-plugin-singlefile
  vite.config.ts         # builds to ../pixie/assets/
  README.md              # frontend dev & build instructions

tests/
  README.md              # testing instructions and manual verification guide
  pixie/                 # automated tests (pytest)
    cli/
      test_test_command.py   # CLI unit tests
      e2e_fixtures/          # mock evaluators and datasets for e2e
    evals/
      test_scorecard.py
    instrumentation/
      test_spans.py
      test_context.py
      test_queue.py
      test_processor.py
      test_integration.py
  manual/                # manual testing fixtures (not run by pytest)
    mock_evaluators.py
    datasets/
      sample-qa.json     # run with: pixie test tests/manual/datasets/sample-qa.json

specs/                   # design specs and architecture docs
```

**Test file naming:**

- Test files must start with `test_` prefix
- Mirror the structure of the source code directory
- One test file per source module

---

## uv Package Management

This project uses **uv** (not pip, Poetry, or conda) for all dependency and environment management.

### Common Commands

```bash
uv sync                          # Install/sync all dependencies (creates .venv if needed)
uv add <package>                 # Add a runtime dependency
uv add --dev <package>           # Add a dev dependency
uv run pytest                    # Run a command inside the managed environment
uv run mypy pixie/               # Type check
uv run ruff check .              # Lint
uv run ruff format .             # Format
uv build                         # Build the package (sdist + wheel)
uv lock                          # Re-lock dependencies after editing pyproject.toml
```

### Rules

- **Never use `pip install` directly** — all dependency changes go through `uv add` / `uv remove` and are recorded in `pyproject.toml`.
- **Always run tools through `uv run`** to ensure the correct virtualenv is used (e.g., `uv run pytest`, not bare `pytest`, unless the venv is already activated).
- **Commit `uv.lock`** alongside `pyproject.toml` changes.

---

## Test-Driven Development (TDD) Requirements

This project follows strict TDD practices to ensure code quality and maintainability.

### 1. Test-First Development

**CRITICAL**: Always write or verify tests BEFORE implementing features or making changes.

**Development Workflow:**

1. **Understand the requirement**: Clarify what needs to be built or changed
2. **Write the test first**: Create test cases that define expected behavior
3. **Run the test**: Verify it fails (red) — this confirms the test is valid
4. **Implement the code**: Write minimal code to make the test pass
5. **Run the test again**: Verify it passes (green)
6. **Refactor if needed**: Improve code while keeping tests green
7. **Run all tests**: Ensure no regressions

### 2. Test Location and Organization

**All tests for the pixie module must be in the `tests/pixie/` directory:**

```
pixie/
  instrumentation/
    spans.py
    handler.py
    wrap.py
    processor.py
    queue.py
    instrumentors.py

tests/
  pixie/
    instrumentation/
      test_spans.py
      test_queue.py
      test_processor.py
```

### 3. Test Coverage Requirements

- **All new code must have tests**: Functions, classes, methods, utilities
- **Bug fixes must include regression tests**: Add a test that would have caught the bug
- **Refactoring must maintain tests**: Verify all existing tests still pass

**What to test:**

- Function inputs and outputs
- Edge cases and boundary conditions
- Error handling and exceptions
- Integration between components
- Span attribute parsing and type conversions
- Handler dispatch and delivery queue behavior

### 4. Running Tests

Before committing changes, always run:

```bash
uv run pytest                            # Run all tests
uv run pytest tests/pixie/              # Run only pixie tests
uv run pytest tests/pixie/instrumentation/test_spans.py  # Run specific test file
uv run pytest -k "test_function_name"   # Run specific test
uv run pytest --cov=pixie               # Run with coverage report
```

### 4a. End-to-End Verification for `pixie test`

The `pixie test` CLI command uses **dataset-driven mode** — each dataset
JSON file specifies evaluators per row. There is no test-file mode.

**Fixture layout:**

```
tests/pixie/cli/
  e2e_fixtures/
    datasets/
      customer-faq.json          # 5-item golden dataset with evaluators per row
    mock_evaluators.py           # Deterministic mock evaluators (no LLM calls)

tests/manual/
  datasets/
    sample-qa.json               # 5-item sample dataset with evaluators per row
  mock_evaluators.py             # SimpleFactualityEval, StrictKeywordEval
```

**Mock evaluators** (`e2e_fixtures/mock_evaluators.py`) are deterministic
replacements for LLM-as-judge evaluators. They use string similarity, keyword
overlap, or fixed scores to produce realistic but reproducible results:

- `MockFactualityEval` — SequenceMatcher string similarity (most items pass)
- `MockClosedQAEval` — keyword overlap ratio (strict; some items fail)
- `MockHallucinationEval` — always returns score 0.95
- `MockFailingEval` (name="MockStrictTone") — always returns score 0.2

**When to run e2e verification:**

Run manual e2e verification whenever you change anything in:

- `pixie/cli/test_command.py` — the `pixie test` entry point
- `pixie/cli/main.py` — CLI argument parsing and forwarding
- `pixie/evals/dataset_runner.py` — dataset loading and evaluator resolution
- `pixie/evals/scorecard.py` — scorecard models, HTML generation
- `pixie/evals/criteria.py` — pass criteria

**Agent verification protocol:**

After making changes to CLI/eval/scorecard code, manually verify `pixie test`
output using both console inspection and Playwright-based scorecard verification.

1. **Run the manual fixture directly:**

   ```bash
   export PIXIE_ROOT=/tmp/pixie_e2e_verify
   uv run pixie test tests/manual/datasets/sample-qa.json --no-open
   ```

2. **Inspect the console output** — verify that:
   - All 5 dataset entries appear with correct ✓/✗ marks
   - Evaluator names are shown per row (e.g. `(SimpleFactualityEval, StrictKeywordEval)`)
   - Scores are shown (e.g. `[1.00, 1.00]`)
   - The scorecard file path is printed at the end
   - No unexpected errors or tracebacks

3. **Inspect the HTML scorecard with Playwright** — write a Playwright script to:
   - Open the generated HTML file via `file://` URL
   - Verify evaluator names appear (SimpleFactualityEval, StrictKeywordEval)
   - Verify per-input score cells show reasonable numeric values
   - Verify PASS/FAIL badges are present
   - Check that "details" links exist and clicking one opens the evaluation detail modal
   - Take a screenshot for visual confirmation
   - Example:

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

4. **Evaluate holistically** — given the dataset contents and evaluator
   definitions, do the scores and pass/fail outcomes make sense?

This verification catches rendering issues, layout regressions, and semantic
correctness problems that simple string assertions can miss.

### 5. Test Quality Guidelines

**Good tests are:**

- **Focused**: Test one thing at a time
- **Independent**: Don't depend on other tests or execution order
- **Readable**: Clear arrange-act-assert structure
- **Fast**: Use mocks/fixtures for external dependencies (OTel, LLM providers)
- **Maintainable**: Easy to update when requirements change

**Example test structure:**

```python
import pytest
from pixie.instrumentation.spans import LLMSpan, ObserveSpan, UserMessage, TextContent


class TestUserMessage:
    """Tests for UserMessage factory methods."""

    def test_from_text_creates_single_text_content(self) -> None:
        # Arrange & Act
        msg = UserMessage.from_text("hello")

        # Assert
        assert msg.content == (TextContent(text="hello"),)
        assert msg.role == "user"

    def test_frozen_span_raises_on_mutation(self) -> None:
        # Arrange
        span = ObserveSpan(
            span_id="abc123",
            trace_id="def456",
            parent_span_id=None,
            started_at=...,
            ended_at=...,
            duration_ms=0.0,
            name="test",
            input=None,
            output=None,
            metadata={},
            error=None,
        )

        # Act & Assert
        with pytest.raises(AttributeError):
            span.name = "mutated"  # type: ignore[misc]
```

### 6. Fixtures and Test Utilities

Use pytest fixtures for common setup:

```python
# In tests/pixie/conftest.py
import pytest
from pixie.instrumentation.handler import InstrumentationHandler
from pixie.instrumentation.spans import LLMSpan, ObserveSpan


class RecordingHandler(InstrumentationHandler):
    """Test handler that records all delivered spans."""

    def __init__(self) -> None:
        self.llm_spans: list[LLMSpan] = []
        self.observe_spans: list[ObserveSpan] = []

    def on_llm(self, span: LLMSpan) -> None:
        self.llm_spans.append(span)

    def on_observe(self, span: ObserveSpan) -> None:
        self.observe_spans.append(span)


@pytest.fixture
def recording_handler() -> RecordingHandler:
    return RecordingHandler()
```

---

## Type Safety Requirements

This project uses Python type hints with strict type checking via **both mypy and Pylance**. Both must be clean because they use different inference engines and can catch different classes of errors. Pylance in particular will catch type mismatches with third-party libraries that mypy may miss when those libraries lack `py.typed` markers.

### 1. Always Run Type Checking

Before committing, verify there are no type errors:

```bash
uv run mypy pixie/               # Type check pixie module
uv run mypy tests/pixie/         # Type check tests
uv run mypy .                    # Type check entire project
```

Also **check Pylance diagnostics** in VS Code — use the Problems panel or the Pylance language server. Zero errors in both mypy and Pylance are required before committing.

Run these commands after making changes to ensure type safety.

### 2. Type Annotation Rules

**CRITICAL**: All function signatures must have type annotations for parameters and return values.

**❌ WRONG** — Missing type annotations:

```python
def process_span(span, attrs):
    return extract_messages(attrs)

def calculate_duration(start, end):
    return (end - start) / 1e6
```

**✅ CORRECT** — Proper type annotations:

```python
from __future__ import annotations
from pixie.instrumentation.spans import LLMSpan, Message

def process_span(span: ReadableSpan, attrs: dict[str, Any]) -> LLMSpan:
    return _build_llm_span(span, attrs)

def calculate_duration(start: int, end: int) -> float:
    return (end - start) / 1e6
```

### 3. Type Safety for Common Patterns

**Union types (use `|` syntax, not `Optional` or `Union`):**

```python
def get_parent_id(span: ReadableSpan) -> str | None:
    if span.parent is not None:
        return format(span.parent.span_id, "016x")
    return None
```

**Frozen dataclasses:**

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class TextContent:
    text: str
    type: Literal["text"] = "text"
```

**Protocol and Abstract Base Classes:**

```python
from abc import ABC, abstractmethod

class InstrumentationHandler(ABC):
    def on_llm(self, span: LLMSpan) -> None:
        pass

    def on_observe(self, span: ObserveSpan) -> None:
        pass
```

### 4. Avoid Type Checking Bypass

**❌ NEVER do this:**

```python
data = fetch_data()  # type: ignore
result: Any = process(data)
value = cast(str, unknown_value)  # Avoid cast unless absolutely necessary
```

**✅ CORRECT approach:**

```python
from typing import TypeGuard

def is_llm_span(attrs: dict[str, Any]) -> bool:
    return attrs.get("openinference.span.kind") == "LLM"

if is_llm_span(attrs):
    process_llm_span(attrs)
```

---

## Code Quality Tools

### 1. Linting and Formatting

```bash
uv run ruff check .              # Run linter
uv run ruff format .             # Format code
```

### 2. Pre-commit Checks

Before committing, run:

```bash
uv run pytest                    # All tests must pass (includes e2e)
uv run mypy pixie/               # Zero type errors
uv run ruff check .              # No linting errors
```

When changing `pixie test` or scorecard-related code, also run the
**agent verification protocol** (section 4a) — run `pixie test` on the manual
fixture and inspect console output + scorecard HTML with Playwright.

Also verify **zero Pylance errors** in VS Code Problems panel (Pylance can catch type mismatches that mypy misses for untyped third-party packages).

---

## Incremental Development

**CRITICAL**: Implement changes incrementally, one small task at a time. This ensures stability and makes debugging easier.

### Development Workflow

1. **Break down the work**: Split large features into small, independent tasks
2. **Before starting each task**:
   - Run `uv run pytest` — ensure existing tests pass
   - Run `uv run mypy pixie/` — ensure no type errors
   - Check Pylance Problems panel — ensure no Pylance errors
3. **Implement one small task**
4. **After completing each task**:
   - Run `uv run pytest` — verify tests still pass
   - Run `uv run mypy pixie/` — verify no new type errors
   - Check Pylance Problems panel — verify no new Pylance errors
   - Fix any issues before moving to next task
5. **Repeat** for each task

**Example of task breakdown:**

❌ **WRONG** — One big task:

- "Implement the LLM span processor"

✅ **CORRECT** — Small incremental tasks:

1. Add span identity extraction (span_id, trace_id, parent_span_id)
2. Add token usage extraction
3. Add request parameter parsing from invocation_parameters
4. Add input message parsing (system, user, assistant, tool roles)
5. Add output message parsing with finish_reasons
6. Add tool definition parsing
7. Add error handling and fallback behavior
8. Add integration test with full pipeline

---

## Code Reuse and DRY Principles

**CRITICAL**: Avoid duplicating code. Always scan the codebase for existing similar code before adding new code.

### Before Writing New Code

1. **Search for existing implementations**:
   - Use semantic search or grep to find similar functionality
   - Check `pixie/` for existing utilities and helpers
   - Check `pixie/instrumentation/` for span processing patterns

2. **Evaluate reusability**:
   - Can existing code be used directly?
   - Can existing code be extended or modified?
   - Should you extract a shared helper?

### When to Extract Shared Code

**Extract a shared helper/module when:**

- The same logic appears in 2+ places
- Similar patterns with minor variations exist
- A piece of code could benefit other parts of the codebase

**Patterns for shared code:**

- **Utility functions**: Place in appropriate module or create `pixie/utils.py`
- **Base classes**: Use ABCs for common interfaces (`InstrumentationHandler`)
- **Type definitions**: Keep span types in `pixie/instrumentation/spans.py`
- **Constants**: Place in relevant module

---

## Documentation and Changelog Requirements

**Every code change must include corresponding documentation updates. Documentation is part of implementation, not a follow-up task.**

### What to Keep Up to Date

- **README files**: Each major directory that contains non-trivial code or assets must have its own `README.md` explaining purpose, usage, and build/test commands. Currently required READMEs:
  - `README.md` (root) — project overview, getting started
  - `docs/package.md` — Python package API reference
  - `frontend/README.md` — React scorecard dev & build instructions
  - `pixie/assets/README.md` — build artifact purpose and rebuild instructions
  - `tests/README.md` — test organization, running tests, manual verification
- **Module / API docstrings**: Update public function, class, and method docstrings whenever behavior, parameters, or return values change.
- **Specs**: Update relevant files in `specs/` (for example `specs/instrumentation.md`) when architecture, data flow, or instrumentation behavior changes.

### README Scoping Rules

**CRITICAL**: When a change introduces a new directory, adds build artifacts, or changes how a subsystem works, the relevant README(s) must be created or updated in the same change set.

**Which READMEs to update:**

| Change type                                   | READMEs to update                                                  |
| --------------------------------------------- | ------------------------------------------------------------------ |
| New top-level directory (e.g., `frontend/`)   | Create `<dir>/README.md` + update root `README.md`                 |
| New package directory (e.g., `pixie/assets/`) | Create `<dir>/README.md` + update `docs/package.md`                |
| New test fixtures or test directories         | Update `tests/README.md`                                           |
| CLI or scorecard changes                      | Update `docs/package.md` + `tests/README.md` (manual verification) |
| Build process changes                         | Update `frontend/README.md` + `pixie/assets/README.md`             |
| API changes                                   | Update `docs/package.md` + relevant module docstrings              |

### Changelog per Feature

**Every non-trivial feature or bug fix must have a changelog entry.**

1. Create or update a file under `changelogs/` named after the feature, e.g. `changelogs/span-processor-error-handling.md`.
2. The file must include:
   - **What changed** and why.
   - **Files affected** (modules, tests, specs, READMEs).
   - **Migration notes** if any API behavior changed.
3. Commit the changelog file together with the implementation.

### Documentation Checklist (Before Every Commit)

1. ✅ All new/changed public functions and classes have accurate docstrings.
2. ✅ All relevant `README.md` files are up to date (see scoping rules above).
3. ✅ Relevant `specs/` docs are updated for architecture or behavior changes.
4. ✅ A `changelogs/<feature>.md` file exists for each non-trivial change.
5. ✅ `tests/README.md` is updated if test structure or manual verification steps changed.

### Hard Completion Gate (Non-Negotiable)

For any non-trivial implementation, a task is **not complete** until all of the following exist and are updated in the same change set:

1. Relevant `README.md` updates (see README scoping rules — may be multiple files)
2. Relevant `specs/*.md` update (design/behavior/architecture)
3. `changelogs/<feature>.md` entry (what changed, files, migration notes)
4. `tests/README.md` update if test structure or manual verification changed

If any of these are missing, the agent must continue working and add them before declaring completion.

### New Directory / Package Delivery Minimum

When introducing a new directory or subpackage, documentation must include:

- A `README.md` in the new directory explaining purpose, contents, and usage
- Update to the parent or root README referencing the new directory
- A minimal runnable usage example (in the README or a test fixture)
- Testing / validation commands relevant to the module
- A dedicated changelog entry for that module delivery

### Automatic Documentation Updates After Every Change

After each code change, immediately:

1. Update docstrings in the same edit.
2. Update all relevant `README.md` files (see README scoping rules).
3. Update relevant `specs/` docs for design or behavior changes.
4. Create/update a changelog file for non-trivial changes.
5. Update `tests/README.md` if test fixtures or verification steps changed.

Do not defer documentation work to the end of a task.

---

## Error Handling Rules

This project has strict error-handling conventions due to operating inside OTel pipelines and background threads:

1. **Never raise from `LLMSpanProcessor.on_end()`** — entire body must be wrapped in try/except
2. **Never raise from `_DeliveryQueue._worker()`** — each iteration must be wrapped
3. **Never raise from `submit()`** — drop silently on full queue, increment counter
4. **Handler method exceptions are silently swallowed** — the handler must not crash the delivery thread
5. **Malformed JSON in span attributes** — fall back to `{}` or `None`, never raise

---

## Summary Checklist

**Before every commit:**

1. ✅ Write/update tests in `tests/pixie/` for your changes
2. ✅ Run `uv run pytest` — all tests must pass
3. ✅ Run `uv run mypy pixie/` — zero type errors allowed
4. ✅ Check Pylance Problems panel — zero Pylance errors allowed
5. ✅ Run `uv run ruff check .` — no linting errors
6. ✅ Update docstrings / `README.md` / relevant `specs/` docs
7. ✅ Add/update `changelogs/<feature>.md` for non-trivial changes
8. ✅ Verify functionality works as expected
9. ✅ If touching `pixie test` / scorecard / dataset runner / eval code, run the **agent verification protocol** (section 4a) — run `pixie test` on the manual fixture and inspect console output + scorecard HTML with Playwright
10. ✅ All relevant `README.md` files are updated (see Documentation section — README Scoping Rules)

**Development cycle:**

1. Break down work into small tasks
2. Before each task: run tests and type check
3. Search codebase for existing similar code
4. Write test first in `tests/pixie/` (TDD)
5. Implement feature (reuse existing code when possible)
6. After each task: run tests and type check
7. Run linting (`uv run ruff check .`)
8. Run **agent verification protocol** (section 4a) if CLI/eval/scorecard code changed
9. Update docs and changelog for the task
10. Fix any issues
11. Commit

Following these practices ensures high code quality, type safety, maintainability, and reliability.
