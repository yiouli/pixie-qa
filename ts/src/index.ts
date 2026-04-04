/**
 * pixie-qa — automated quality assurance for AI applications.
 *
 * Re-exports the full public API so users can import from "pixie-qa"
 * for every commonly used symbol without needing submodule paths.
 */

// -- Instrumentation ---------------------------------------------------------
export { StorageHandler, enableStorage } from "./instrumentation/handlers";
export {
  addHandler,
  removeHandler,
  flush,
  init,
  observe,
  startObservation,
} from "./instrumentation/observation";

// -- Storage -----------------------------------------------------------------
export { UNSET, asEvaluable } from "./storage/evaluable";
export type { Evaluable } from "./storage/evaluable";
export { ObservationStore } from "./storage/store";
export { ObservationNode, buildTree } from "./storage/tree";

// -- Dataset -----------------------------------------------------------------
export { DatasetStore } from "./dataset/store";
export type { Dataset } from "./dataset/models";

// -- Evals -------------------------------------------------------------------
export { evaluate, createEvaluation } from "./evals/evaluation";
export type { Evaluation, Evaluator } from "./evals/evaluation";
export { ScoreThreshold } from "./evals/criteria";
export type { PassCriteria } from "./evals/criteria";
export {
  EvalAssertionError,
  assertPass,
  assertDatasetPass,
  runAndEvaluate,
} from "./evals/evalUtils";
export { createLlmEvaluator } from "./evals/llmEvaluator";
export { configureRateLimits } from "./evals/rateLimiter";
export type { EvalRateLimiter } from "./evals/rateLimiter";
export { MemoryTraceHandler, captureTraces } from "./evals/traceCapture";
export { lastLlmCall, root } from "./evals/traceHelpers";

// -- Scorers -----------------------------------------------------------------
export {
  AutoevalsAdapter,
  LevenshteinMatch,
  ExactMatch,
  NumericDiff,
  JSONDiff,
  ValidJSON,
  ListContains,
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
} from "./evals/scorers";

// -- Config ------------------------------------------------------------------
export { getConfig } from "./config";
export type { PixieConfig, RateLimitConfig } from "./config";

// -- DAG ---------------------------------------------------------------------
export {
  isValidDagName,
  parseDag,
  validateDag,
  generateMermaid,
} from "./dag/index";
export type { DagNode, ValidationResult } from "./dag/index";
export { checkTraceAgainstDag, checkLastTrace } from "./dag/traceCheck";
export type { TraceCheckResult } from "./dag/traceCheck";
