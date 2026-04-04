/**
 * Test result models and persistence for `pixie test`.
 */
import type { JsonValue } from "../storage/evaluable";
/** Result of a single evaluator on a single entry. */
export interface EvaluationResult {
    readonly evaluator: string;
    readonly score: number;
    readonly reasoning: string;
}
/** Results for a single dataset entry. */
export interface EntryResult {
    readonly input: JsonValue;
    readonly output: JsonValue;
    readonly expectedOutput: JsonValue | null;
    readonly description: string | null;
    readonly evaluations: EvaluationResult[];
}
/** Results for a single dataset evaluation run. */
export interface DatasetResult {
    dataset: string;
    entries: EntryResult[];
    analysis: string | null;
}
/** Top-level test run result container. */
export interface RunResult {
    testId: string;
    command: string;
    startedAt: string;
    endedAt: string;
    datasets: DatasetResult[];
}
/** Generate a timestamped test run ID (YYYYMMDD-HHMMSS). */
export declare function generateTestId(): string;
/**
 * Write test result JSON to `<pixie_root>/results/<testId>/result.json`.
 *
 * @returns The absolute path of the saved JSON file.
 */
export declare function saveTestResult(result: RunResult): string;
/**
 * Load a test result from `<pixie_root>/results/<testId>/result.json`.
 *
 * Also reads any `dataset-<index>.md` analysis files.
 */
export declare function loadTestResult(testId: string): RunResult;
//# sourceMappingURL=testResult.d.ts.map