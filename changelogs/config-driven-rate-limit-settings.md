# Config-Driven Rate Limit Settings

## What changed

- Moved evaluator rate-limit settings under the central `PixieConfig` model instead of treating them as a standalone config path.
- `get_config()` now loads the nearest `.env` from the current working directory at call time, while preserving already-exported environment variables.
- Added `PIXIE_RATE_LIMIT_ENABLED` plus `PIXIE_RATE_LIMIT_RPS`, `PIXIE_RATE_LIMIT_RPM`, `PIXIE_RATE_LIMIT_TPS`, and `PIXIE_RATE_LIMIT_TPM` support.
- `pixie test` now applies the central config before evaluator execution, so `.env`-backed rate limits are honored automatically.
- Replaced the old rate-limit default tests with config-integration coverage and added a CLI regression test for `pixie test`.

## Files affected

- `pixie/config.py`
- `pixie/evals/rate_limiter.py`
- `pixie/cli/test_command.py`
- `tests/pixie/test_config.py`
- `tests/pixie/evals/test_rate_limiter.py`
- `tests/pixie/cli/test_test_command.py`
- `README.md`
- `docs/package.md`
- `tests/README.md`
- `specs/usability-utils.md`
- `specs/evals-harness.md`

## Migration notes

- Existing manual `configure_rate_limits(RateLimitConfig(...))` calls still work.
- To manage evaluator throttling through project config instead, set `PIXIE_RATE_LIMIT_ENABLED=true` and any optional `PIXIE_RATE_LIMIT_*` overrides in your shell or `.env` file.
