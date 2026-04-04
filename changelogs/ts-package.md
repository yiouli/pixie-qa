# Changelog: TypeScript pixie-qa Package

## What Changed

Added comprehensive test suite (133 tests across 10 files) and documentation for the TypeScript `pixie-qa` package.

### Test Files Created

- `ts/tests/config.test.ts` — `getConfig()` defaults and env var overrides
- `ts/tests/evaluable.test.ts` — UNSET sentinel, Evaluable creation, `asEvaluable()` for ObserveSpan and LLMSpan
- `ts/tests/spans.test.ts` — Span type creation, message/content factory helpers
- `ts/tests/tree.test.ts` — `ObservationNode`, `buildTree()`, `find()`, `findByType()`, `toText()`
- `ts/tests/evaluation.test.ts` — `createEvaluation()`, `evaluate()` with sync/async evaluators, score clamping
- `ts/tests/criteria.test.ts` — `ScoreThreshold` pass/fail scenarios
- `ts/tests/datasetStore.test.ts` — `DatasetStore` CRUD operations
- `ts/tests/rateLimiter.test.ts` — `EvalRateLimiter`, `configureRateLimits()`, `getRateLimiter()`
- `ts/tests/serialization.test.ts` — `serializeSpan()`/`deserializeSpan()` round-trip for both span types
- `ts/tests/traceHelpers.test.ts` — `lastLlmCall()` and `root()` functions

### Documentation Created

- `ts/README.md` — Package overview, installation, CLI usage, programmatic API, Python↔TS naming conventions

## Files Affected

- `ts/tests/` — 10 new test files
- `ts/README.md` — New documentation
- `changelogs/ts-package.md` — This changelog

## Migration Notes (Python → TypeScript)

The TypeScript package follows `camelCase` naming conventions instead of Python's `snake_case`:

- `get_config()` → `getConfig()`
- `eval_input` → `evalInput`
- `start_observation()` → `startObservation()`
- `build_tree()` → `buildTree()`
- `last_llm_call()` → `lastLlmCall()`
- Package name: `pixie` (Python) → `pixie-qa` (npm)
