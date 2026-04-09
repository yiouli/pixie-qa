# Deterministic Analysis

## What changed

Rewrote `pixie analyze` from an OpenAI-dependent LLM call into fully deterministic
data preparation. The command now computes statistics, clusters failures, and formats
trace data into structured markdown — no LLM calls, no API keys required.

### Per-dataset output (`dataset-{i}.md`)

- Overview section with pass/fail counts and pass rate
- Per-Evaluator Statistics table (pass rate, min, max, mean, stddev)
- Failure Clusters — entries grouped by their set of failed evaluators
- Trace Summary table (models used, token counts, latency, errors per entry)
- Entry Details with per-entry evaluator scores and trace tables

### Cross-dataset output (`summary.md`)

- Aggregate statistics across all datasets
- Evaluator consistency (pass rates across datasets)
- Common failure patterns
- Aggregate trace statistics (total LLM calls, models, tokens, latency)

### Other changes

- `analyze()` entry point is now synchronous (no `asyncio.run`)
- `analyze()` requires no environment variables (`OPENAI_API_KEY` not needed)
- The only argument is `test_id`

## Files affected

- `pixie/cli/analyze_command.py` — complete rewrite (removed all OpenAI/async code)
- `tests/pixie/cli/test_analyze_command.py` — complete rewrite (15 tests)

## Migration notes

- `pixie analyze` no longer requires `OPENAI_API_KEY` in the environment.
- The output markdown format has changed — it now has structured sections with
  tables instead of free-form LLM-generated prose.
- The `analyze()` function is now synchronous (returns `int`, no `async`).
