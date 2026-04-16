# pixie-ts

TypeScript port of the `pixie-qa` Python package — eval-driven development for AI applications.

This package provides the same functionality as the Python `pixie-qa` package, with TypeScript-idiomatic naming (camelCase) and native implementations.

## Install

```bash
npm install
npm run build
```

## CLI

All Python `pixie` commands are available via `npx pixie-qa`:

| Command | Description |
| --- | --- |
| `npx pixie-qa test [path]` | Run eval tests |
| `npx pixie-qa init [root]` | Scaffold the `pixie_qa/` working directory |
| `npx pixie-qa start [root]` | Launch the web UI |
| `npx pixie-qa stop [root]` | Stop the web UI server |
| `npx pixie-qa trace --runnable R --input I --output O` | Run a Runnable and capture trace to JSONL |
| `npx pixie-qa format --input I --output O` | Convert a trace JSONL to a dataset entry JSON |

## Package Structure

```text
pixie-ts/
  src/
    index.ts                      # Top-level barrel exports
    config.ts                     # PixieConfig from PIXIE_* env vars
    cli/
      main.ts                     # CLI entry point (Commander.js)
      testCommand.ts              # pixie-qa test
      initCommand.ts              # pixie-qa init
      startCommand.ts             # pixie-qa start
      stopCommand.ts              # pixie-qa stop
      traceCommand.ts             # pixie-qa trace
      formatCommand.ts            # pixie-qa format
    eval/
      index.ts                    # Eval module re-exports
      evaluable.ts                # TestCase, Evaluable, NamedData types
      evaluation.ts               # Evaluator type, evaluate() with clamping
      agentEvaluator.ts           # Agent-deferred evaluator factory
      llmEvaluator.ts             # LLM-as-judge evaluator with OpenAI
      rateLimiter.ts              # Sliding-window rate limiter (RPS/RPM/TPS/TPM)
      scorers.ts                  # 21 built-in evaluators (6 heuristic + 15 LLM)
    instrumentation/
      index.ts                    # Instrumentation module re-exports
      llmTracing.ts               # Span types, InstrumentationHandler, handler registry
      wrap.ts                     # wrap() API with AsyncLocalStorage context
      models.ts                   # Trace log record types (InputDataLog, LLMSpanLog)
    harness/
      index.ts                    # Harness module re-exports
      runnable.ts                 # Runnable protocol (setup/run/teardown)
      runResult.ts                # Result types and JSONL persistence
      runner.ts                   # Dataset loading, evaluator resolution, concurrent execution
  tests/
    *.test.ts                     # Unit tests (vitest)
    e2e.test.ts                   # E2E tests for dataset loading and result persistence
    e2e-pipeline.test.ts          # Full-pipeline E2E test with mock evaluators
    manual/
      mock_evaluators.ts          # Deterministic evaluators for manual verification
      datasets/
        sample-qa.json            # 5-item sample dataset
    e2e_fixtures/
      mock_evaluators.ts          # Deterministic evaluators for automated E2E
      datasets/
        customer-faq.json         # 5-item customer FAQ dataset
```

## Naming Convention

Python snake_case names are converted to TypeScript camelCase:

| Python | TypeScript |
| --- | --- |
| `create_agent_evaluator()` | `createAgentEvaluator()` |
| `create_llm_evaluator()` | `createLlmEvaluator()` |
| `enable_llm_tracing()` | `enableLlmTracing()` |
| `eval_input` | `evalInput` |
| `wrap(purpose="input", name="x")` | `wrap(data, { purpose: "input", name: "x" })` |

## Evaluators

### Heuristic (no API calls)

| Evaluator | Description |
| --- | --- |
| `LevenshteinMatch` | Edit-distance string similarity |
| `ExactMatch` | Exact value comparison |
| `NumericDiff` | Normalised numeric difference |
| `JSONDiff` | Structural JSON comparison |
| `ValidJSON` | JSON syntax validation |
| `ListContains` | List overlap scoring |

### LLM-as-judge (requires OpenAI API key)

`Factuality`, `ClosedQA`, `Battle`, `Humor`, `Security`, `Sql`, `Summary`, `Translation`, `Possible`, `Moderation`, `EmbeddingSimilarity`, `ContextRelevancy`, `Faithfulness`, `AnswerRelevancy`, `AnswerCorrectness`

## Configuration

Configuration is read from environment variables (with `.env` support via dotenv):

| Variable | Description |
| --- | --- |
| `PIXIE_ROOT` | Root directory for generated artefacts |
| `PIXIE_DATASET_DIR` | Dataset directory override |
| `PIXIE_RATE_LIMIT_ENABLED` | `true` to enable evaluator throttling |
| `PIXIE_RATE_LIMIT_RPS` | Max requests per second |
| `PIXIE_RATE_LIMIT_RPM` | Max requests per minute |
| `PIXIE_RATE_LIMIT_TPS` | Max tokens per second |
| `PIXIE_RATE_LIMIT_TPM` | Max tokens per minute |
| `PIXIE_TRACING` | `true` to enable tracing |
| `PIXIE_TRACE_OUTPUT` | Trace output file path |

## Testing

```bash
# Run all tests (unit + e2e)
npm test

# Type-check src only
npx tsc --noEmit

# Type-check src + tests
npx tsc --noEmit --project tsconfig.check.json
```

### Manual Verification

When changing CLI, eval, or harness code, run the manual fixture:

```bash
PIXIE_ROOT=/tmp/pixie_ts_e2e npx pixie-qa test tests/manual/datasets/sample-qa.json --no-open
```

Verify:

- All 5 entries appear with evaluator names and scores
- No unexpected errors
- Result directory is created at the path printed

### Test Structure

| Test file | Coverage |
| --- | --- |
| `config.test.ts` | Environment variable parsing, defaults |
| `evaluable.test.ts` | TestCase, Evaluable creation, collapseNamedData |
| `evaluation.test.ts` | Score clamping, error propagation |
| `agentEvaluator.test.ts` | AgentEvaluationPending, factory function |
| `rateLimiter.test.ts` | Sliding window, singleton management |
| `scorers.test.ts` | All 6 heuristic evaluators |
| `llmTracing.test.ts` | Handler registry, span submission, error swallowing |
| `wrap.test.ts` | Wrap context, input injection, output capture |
| `models.test.ts` | Trace log record factories |
| `runnable.test.ts` | isRunnableClass, argsSchema extraction |
| `runResult.test.ts` | generateTestId, result type guards, entry helpers |
| `runner.test.ts` | Evaluator name resolution, builtin list |
| `e2e.test.ts` | Dataset discovery, loading, validation, result persistence |
| `e2e-pipeline.test.ts` | Full pipeline: load → run → evaluate → save with mock evaluators |

## Technology Stack

- **TypeScript** (ES2022, strict mode)
- **Node.js 18+**
- **Commander.js** — CLI framework
- **Zod** — runtime schema validation
- **OpenAI SDK** — LLM-as-judge evaluators
- **Vitest** — test runner
- **dotenv** — .env file support
- **AsyncLocalStorage** — context propagation (replaces Python contextvars)
