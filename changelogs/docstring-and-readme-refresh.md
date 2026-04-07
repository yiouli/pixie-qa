# Docstring and README Refresh

## What Changed

Updated all outdated docstrings across the `pixie/` package and rewrote `docs/package.md` to accurately reflect the current API surface.

## Why

The codebase underwent significant restructuring (modules renamed from `pixie.evals` to `pixie.eval`, storage layer removed, `enable_storage()`/`@observe`/`start_observation` replaced by `enable_llm_tracing()`/`wrap()`, old dataset CLI commands removed, etc.) but documentation had not been updated to match.

## Files Affected

### Docstring fixes

- `pixie/__init__.py` — removed duplicate entries in `__all__`
- `pixie/eval/__init__.py` — removed references to non-existent `ScoreThreshold`, `DatasetEntryResult`, `DatasetScorecard`, `generate_dataset_scorecard_html`, `save_dataset_scorecard`
- `pixie/eval/scorers.py` — fixed `AutoevalsAdapter` cross-reference from `pixie.storage.evaluable` to `pixie.eval.evaluable`; updated module docstring re-export reference from `pixie.evals` to `pixie.eval`
- `pixie/eval/llm_evaluator.py` — fixed `create_llm_evaluator` cross-reference from `pixie.storage.evaluable` to `pixie.eval.evaluable`
- `pixie/cli/__init__.py` — replaced reference to non-existent `pixie-test` entry point with actual subcommand list
- `pixie/instrumentation/__init__.py` — replaced `init()` with `enable_llm_tracing()` throughout; expanded documentation of span, message, and wrap types
- `pixie/instrumentation/llm_tracing.py` — replaced `init()` references with `enable_llm_tracing()` in docstrings and error messages
- `pixie/web/__init__.py` — expanded thin one-liner docstring to describe submodules
- `pixie/harness/__init__.py` — added module docstring (was empty)

### README updates

- `docs/package.md` — comprehensive rewrite: removed all references to `enable_storage()`, `@observe`, `start_observation`, `assert_dataset_pass`, `assert_pass`, `FactualityEval`, `ExactMatchEval`, `ObservationStore`, `pixie.storage`, `pixie.dataset`, old `pixie dataset` CLI commands, `pixie dag` commands, `pixie evaluators list`, SQLite DB config, old evaluator class names (`*Eval` suffix); added documentation for `enable_llm_tracing()`, `wrap()` API, `Runnable` protocol, `create_llm_evaluator`, `pixie trace`/`pixie format` commands, correct dataset JSON schema, correct evaluator names, CLI reference table
- `README.md` — fixed grammar ("make" → "makes")

## Migration Notes

No API changes — documentation only.
