# pixie-qa (TypeScript)

Automated quality assurance for AI applications — TypeScript implementation.

## Installation

```bash
npm install pixie-qa
```

Requires Node.js ≥ 18.

## CLI Usage

```bash
# Initialize project structure
npx pixie-qa init [root]

# Launch web UI for browsing eval artifacts
npx pixie-qa start [root]

# Run evaluations on a dataset
npx pixie-qa test [path] [-v|--verbose] [--no-open]

# Analyze test results with LLM
npx pixie-qa analyze <test_run_id>

# Dataset management
npx pixie-qa dataset create <name>
npx pixie-qa dataset list
npx pixie-qa dataset save <name> [--select root|last_llm_call|by_name]
npx pixie-qa dataset validate [path]

# Trace inspection
npx pixie-qa trace list [--limit N] [--errors]
npx pixie-qa trace show <trace_id> [-v] [--json]
npx pixie-qa trace last [--json]
npx pixie-qa trace verify

# List built-in evaluators
npx pixie-qa evaluators list

# DAG validation
npx pixie-qa dag validate <json_file> [--project-root PATH]
npx pixie-qa dag check-trace <json_file>
```

## Programmatic API

```typescript
import {
  // Instrumentation
  init, observe, startObservation, flush, addHandler, removeHandler,
  StorageHandler, enableStorage,

  // Storage
  UNSET, asEvaluable, ObservationStore, ObservationNode, buildTree,

  // Datasets
  DatasetStore,

  // Evaluation
  evaluate, createEvaluation, ScoreThreshold,
  assertPass, assertDatasetPass, runAndEvaluate,
  EvalAssertionError, createLlmEvaluator,
  configureRateLimits,

  // Trace helpers
  lastLlmCall, root,
  MemoryTraceHandler, captureTraces,

  // Scorers (autoevals wrappers)
  ExactMatch, LevenshteinMatch, Factuality, ClosedQA,

  // Config
  getConfig,

  // DAG
  parseDag, validateDag, generateMermaid, checkTraceAgainstDag,
} from "pixie-qa";
```

### Instrumentation

```typescript
import { init, observe, flush } from "pixie-qa";

init();

const result = await observe("my-task", async (ctx) => {
  ctx.input = { question: "What is AI?" };
  const answer = await myLlmCall(ctx.input.question);
  ctx.output = { answer };
  return answer;
});

await flush();
```

### Evaluation

```typescript
import { evaluate, createEvaluation, ScoreThreshold, assertPass } from "pixie-qa";
import type { Evaluator, Evaluable } from "pixie-qa";

const myEval: Evaluator = (evaluable) =>
  createEvaluation({
    score: evaluable.evalOutput === evaluable.expectedOutput ? 1.0 : 0.0,
    reasoning: "Exact match check",
  });

const result = await evaluate(myEval, evaluable);
```

### Datasets

```typescript
import { DatasetStore } from "pixie-qa";

const store = new DatasetStore();
store.create("my-dataset", [item1, item2]);
const ds = store.get("my-dataset");
store.append("my-dataset", newItem);
store.delete("my-dataset");
```

## Python ↔ TypeScript Naming Conventions

| Concept | Python (`pixie`) | TypeScript (`pixie-qa`) |
|---|---|---|
| Package | `pixie` | `pixie-qa` |
| Config | `get_config()` | `getConfig()` |
| Observation | `start_observation()` | `startObservation()` |
| Evaluable fields | `eval_input`, `eval_output` | `evalInput`, `evalOutput` |
| Expected output | `expected_output` | `expectedOutput` |
| Span IDs | `span_id`, `trace_id` | `spanId`, `traceId` |
| Duration | `duration_ms` | `durationMs` |
| Token counts | `input_tokens` | `inputTokens` |
| Rate limiting | `configure_rate_limits()` | `configureRateLimits()` |
| Assertions | `assert_pass()` | `assertPass()` |
| Tree building | `build_tree()` | `buildTree()` |
| Trace helpers | `last_llm_call()` | `lastLlmCall()` |
| Pass criteria | `ScoreThreshold.__call__()` | `ScoreThreshold.__call__()` |

General pattern: Python uses `snake_case`, TypeScript uses `camelCase`.
