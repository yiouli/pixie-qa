/**
 * pixie-qa — automated quality assurance for AI applications.
 *
 * Top-level re-export barrel file that mirrors the Python `pixie` package's
 * public API, using TypeScript-idiomatic camelCase naming.
 */

// -- config ------------------------------------------------------------------
export { type PixieConfig, type RateLimitConfig, getConfig } from "./config.js";

// -- eval --------------------------------------------------------------------
export {
  // evaluable
  type NamedData,
  type TestCase,
  type Evaluable,
  type JsonValue,
  UNSET,
  type Unset,
  createTestCase,
  createEvaluable,
  collapseNamedData,

  // evaluation
  type Evaluation,
  type Evaluator,
  evaluate,

  // agent evaluator
  AgentEvaluationPending,
  createAgentEvaluator,

  // llm evaluator
  createLlmEvaluator,

  // rate limiter
  EvalRateLimiter,
  configureRateLimits,
  configureRateLimitsFromConfig,
  getRateLimiter,

  // scorers (heuristic)
  LevenshteinMatch,
  ExactMatch,
  NumericDiff,
  JSONDiff,
  ValidJSON,
  ListContains,

  // scorers (LLM-as-judge)
  EmbeddingSimilarity,
  Factuality,
  ClosedQA,
  Battle,
  Humor,
  Security,
  Sql,
  Summary,
  Translation,
  Possible,
  Moderation,
  ContextRelevancy,
  Faithfulness,
  AnswerRelevancy,
  AnswerCorrectness,
} from "./eval/index.js";

// -- instrumentation ---------------------------------------------------------
export {
  // span / message types
  type TextContent,
  type ImageContent,
  type MessageContent,
  type ToolCall,
  type ToolDefinition,
  type SystemMessage,
  type UserMessage,
  type AssistantMessage,
  type ToolResultMessage,
  type Message,
  userMessageFromText,
  type LLMSpan,
  type ObserveSpan,

  // handler
  InstrumentationHandler,
  enableLlmTracing,
  addHandler,
  removeHandler,
  submitLlmSpan,
  submitObserveSpan,
  flush,

  // wrap
  type Purpose,
  type WrappedData,
  filterByPurpose,
  serializeWrapData,
  deserializeWrapData,
  wrap,
  WrapRegistryMissError,
  WrapTypeMismatchError,
  WrapNameCollisionError,
  setEvalInput,
  getEvalInput,
  clearEvalInput,
  initEvalOutput,
  getEvalOutput,
  clearEvalOutput,
  runWithWrapContext,
  runWithWrapContextAsync,

  // models
  INPUT_DATA_KEY,
  type InputDataLog,
  type LLMSpanLog,
  type LLMSpanTrace,
  createInputDataLog,
  createLlmSpanLog,
} from "./instrumentation/index.js";

// -- harness -----------------------------------------------------------------
export {
  type Runnable,
  type RunnableClass,
  isRunnableClass,
  getRunnableArgsSchema,
  generateTestId,
  type EvaluationResult,
  type PendingEvaluation,
  isEvaluationResult,
  type EntryResult,
  type DatasetResult,
  type RunResult,
  entryInput,
  entryOutput,
  saveTestResult,
  loadTestResult,
  BUILTIN_EVALUATOR_NAMES,
  resolveEvaluatorName,
  type DatasetEntry,
  type Dataset,
  discoverDatasetFiles,
  loadDataset,
  resolveRunnableReference,
  evaluateEntry,
  runDataset,
} from "./harness/index.js";
