/**
 * Barrel export for the evals module.
 */

// Evaluation primitives
export type { Evaluation, Evaluator } from "./evaluation";
export { createEvaluation, evaluate } from "./evaluation";

// Pass criteria
export { ScoreThreshold } from "./criteria";
export type { PassCriteria } from "./criteria";

// Autoevals scorers
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
} from "./scorers";

// LLM evaluator
export { createLlmEvaluator } from "./llmEvaluator";

// Rate limiter
export {
  EvalRateLimiter,
  configureRateLimits,
  configureRateLimitsFromConfig,
  getRateLimiter,
} from "./rateLimiter";

// Trace capture
export { MemoryTraceHandler, captureTraces } from "./traceCapture";

// Trace helpers
export { lastLlmCall, root } from "./traceHelpers";

// Eval utils
export {
  EvalAssertionError,
  runAndEvaluate,
  assertPass,
  assertDatasetPass,
} from "./evalUtils";

// Test result
export type {
  EvaluationResult,
  EntryResult,
  DatasetResult,
  RunResult,
} from "./testResult";
export {
  generateTestId,
  saveTestResult,
  loadTestResult,
} from "./testResult";

// Scorecard
export type { DatasetEntryResult, DatasetScorecard } from "./scorecard";
export {
  evaluatorDisplayName,
  createDatasetScorecard,
  generateDatasetScorecardHtml,
  saveDatasetScorecard,
} from "./scorecard";

// Dataset runner
export {
  BUILTIN_EVALUATOR_NAMES,
  resolveEvaluatorName,
  discoverDatasetFiles,
  loadDatasetEntries,
  validateDatasetFile,
  listAvailableEvaluators,
} from "./datasetRunner";
export type { LoadedDataset } from "./datasetRunner";
