/**
 * Dataset-driven test runner for `pixie test`.
 *
 * Processes dataset JSON files where each row specifies its own evaluators.
 * Built-in evaluator names (no dots) are auto-resolved to `pixie-qa.{Name}`.
 * Custom evaluators use fully qualified names.
 */
import type { Evaluable } from "../storage/evaluable";
/** Names of all built-in evaluators. */
export declare const BUILTIN_EVALUATOR_NAMES: ReadonlySet<string>;
/** Parsed dataset ready for evaluation. */
export interface LoadedDataset {
    readonly name: string;
    /** Fully qualified name of the runnable function. */
    readonly runnable: string;
    /** List of [evaluable, evaluatorNames] pairs. */
    readonly entries: Array<[Evaluable, string[]]>;
}
/**
 * Resolve short built-in name to fully qualified, or pass through FQN.
 *
 * @throws if name has no dots and is not a known built-in.
 */
export declare function resolveEvaluatorName(name: string): string;
/** Return sorted list of all built-in evaluator names. */
export declare function listAvailableEvaluators(): string[];
/**
 * Find all dataset JSON files under `searchPath`.
 *
 * Handles file, directory, or `.` for current dir.
 */
export declare function discoverDatasetFiles(searchPath: string): string[];
/**
 * Validate a dataset file and return a list of human-readable errors.
 * Empty list means the file is valid.
 */
export declare function validateDatasetFile(datasetPath: string): string[];
/**
 * Load a dataset and return a LoadedDataset.
 *
 * @throws if the file does not exist or validation fails.
 */
export declare function loadDatasetEntries(datasetPath: string): LoadedDataset;
//# sourceMappingURL=datasetRunner.d.ts.map