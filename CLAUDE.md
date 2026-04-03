# CLAUDE.md — pixie-qa

## Project Overview

pixie-qa is a Python package and coding-agent skill for automated quality assurance of AI applications. Published as `pixie`, it provides instrumentation, evaluation, and observability primitives for LLM-powered apps.

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
    eval_utils.py        # assert_pass / assert_dataset_pass
  instrumentation/
    __init__.py          # public API: init(), start_observation(), observe(), flush()
    spans.py             # ObserveSpan, LLMSpan, message/content types
    handler.py           # InstrumentationHandler ABC
    context.py           # ObservationContext (mutable object yielded by start_observation())
    observe.py           # @observe decorator for automatic input/output capture
    processor.py         # LLMSpanProcessor (OTel SpanProcessor)
    queue.py             # _DeliveryQueue (background worker thread)
    instrumentors.py     # auto-discovers and activates OpenInference instrumentors
    py.typed

frontend/                # React scorecard SPA source
  src/                   # React components, types, styles
  package.json           # React 19, Vite 6, vite-plugin-singlefile
  vite.config.ts         # builds to ../pixie/assets/

tests/
  pixie/                 # automated tests (pytest)
    cli/
      test_test_command.py   # CLI unit tests
      e2e_fixtures/          # mock evaluators and datasets for e2e
    evals/
    instrumentation/
  manual/                # manual testing fixtures (not run by pytest)
    mock_evaluators.py
    datasets/
      sample-qa.json     # run with: pixie test tests/manual/datasets/sample-qa.json

specs/                   # design specs and architecture docs
```

**Test file naming:** prefix `test_`, mirror source directory structure, one file per source module.

---

## Package Management (uv)

**Never use `pip install`** — all dependency changes go through `uv`.

```bash
uv sync                          # Install/sync all dependencies
uv add <package>                 # Add runtime dependency
uv add --dev <package>           # Add dev dependency
uv run pytest                    # Run tests
uv run mypy pixie/               # Type check
uv run ruff check .              # Lint
uv run ruff format .             # Format
uv build                         # Build package
```

Always run tools through `uv run`. Commit `uv.lock` alongside `pyproject.toml` changes.

---

## Test-Driven Development (TDD)

**Write or verify tests BEFORE implementing features.**

**Workflow:**

1. Write test first → verify it fails (red)
2. Implement minimal code → verify it passes (green)
3. Refactor if needed, keeping tests green
4. Run all tests to check for regressions

**All tests for the pixie module must be in `tests/pixie/`.**

### Running Tests

```bash
uv run pytest                                                      # All tests
uv run pytest tests/pixie/                                        # pixie tests only
uv run pytest --cov=pixie                                         # With coverage
```

### E2E Verification for `pixie test`

Run manual e2e verification whenever changing:

- `pixie/cli/test_command.py`
- `pixie/cli/main.py`
- `pixie/evals/dataset_runner.py`
- `pixie/evals/scorecard.py`
- `pixie/evals/eval_utils.py`
- `pixie/evals/criteria.py`

**Agent verification protocol:**

1. Run the manual fixture:

   ```bash
   export PIXIE_ROOT=/tmp/pixie_e2e_verify
   uv run pixie test tests/manual/datasets/sample-qa.json --no-open
   ```

2. Inspect console output — verify all 5 items appear with evaluator names and scores

3. Inspect HTML scorecard with Playwright — verify evaluator names, scores, PASS/FAIL badges, and detail modals

### Test Quality

- **Focused**: one thing per test
- **Independent**: no shared state or execution order dependency
- **Fast**: mock external dependencies (OTel, LLM providers)
- **Clear**: arrange-act-assert structure

---

## Type Safety

Both **mypy** and **Pylance** must be clean (they catch different errors).

```bash
uv run mypy pixie/               # Type check pixie module
uv run mypy tests/pixie/         # Type check tests
```

Also check **Pylance diagnostics** in VS Code Problems panel — zero errors required before committing.

**Rules:**

- All function signatures must have type annotations for parameters and return values
- Use `|` syntax for unions (not `Optional` or `Union`)
- Use `from __future__ import annotations` at top of files
- Avoid `type: ignore`, `Any`, and `cast()` unless absolutely necessary
- Use frozen dataclasses for immutable span types

---

## Code Quality

```bash
uv run ruff check .              # Lint
uv run ruff format .             # Format
```

---

## Incremental Development

Break large features into small, independent tasks. Before and after each task:

```bash
uv run pytest
uv run mypy pixie/
# Check Pylance Problems panel
```

Never implement everything at once. Fix issues between tasks, not at the end.

---

## Code Reuse

Before writing new code, search the codebase for existing similar code. Extract shared helpers when the same logic appears in 2+ places. Keep span types in `pixie/instrumentation/spans.py`, base classes as ABCs.

---

## Documentation Requirements

**Documentation is part of implementation, not a follow-up.**

### README Scoping Rules

| Change type                           | READMEs to update                                      |
| ------------------------------------- | ------------------------------------------------------ |
| New top-level directory               | Create `<dir>/README.md` + update root `README.md`     |
| New package directory                 | Create `<dir>/README.md` + update `docs/package.md`    |
| New test fixtures or test directories | Update `tests/README.md`                               |
| CLI or scorecard changes              | Update `docs/package.md` + `tests/README.md`           |
| Build process changes                 | Update `frontend/README.md` + `pixie/assets/README.md` |
| API changes                           | Update `docs/package.md` + relevant module docstrings  |

### Changelog

Every non-trivial feature or bug fix requires a file under `changelogs/<feature>.md` containing:

- What changed and why
- Files affected
- Migration notes (if API behavior changed)

### Hard Completion Gate

A task is **not complete** until all of the following are updated in the same change set:

1. Relevant `README.md` files
2. Relevant `specs/*.md` (design/behavior/architecture)
3. `changelogs/<feature>.md`
4. `tests/README.md` (if test structure changed)

---

## Error Handling Rules

1. **Never raise from `LLMSpanProcessor.on_end()`** — wrap entire body in try/except
2. **Never raise from `_DeliveryQueue._worker()`** — wrap each iteration
3. **Never raise from `submit()`** — drop silently on full queue
4. **Handler method exceptions are silently swallowed** — must not crash delivery thread
5. **Malformed JSON in span attributes** — fall back to `{}` or `None`, never raise
6. **`start_observation()` block exceptions** — re-raise normally after snapshotting `error` field

---

## Pre-Commit Checklist

1. ✅ Write/update tests in `tests/pixie/`
2. ✅ `uv run pytest` — all tests pass
3. ✅ `uv run mypy pixie/` — zero type errors
4. ✅ Pylance Problems panel — zero errors
5. ✅ `uv run ruff check .` — no linting errors
6. ✅ Docstrings / `README.md` / `specs/` updated
7. ✅ `changelogs/<feature>.md` added/updated
8. ✅ If touching `pixie test`/scorecard/dataset runner/eval: run the **agent verification protocol** — run `pixie test` on the manual fixture and inspect console output + scorecard HTML with Playwright
9. ✅ All relevant `README.md` files updated per scoping rules
