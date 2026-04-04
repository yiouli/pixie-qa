/**
 * Scorecard data models and HTML report generation.
 *
 * Provides DatasetEntryResult, DatasetScorecard types and
 * generateDatasetScorecardHtml(), saveDatasetScorecard() functions.
 */
import type { Evaluation } from "./evaluation";
/** Derive a human-readable name from an evaluator callable. */
export declare function evaluatorDisplayName(evaluator: unknown): string;
/** Evaluation results for a single dataset entry. */
export interface DatasetEntryResult {
    readonly evaluatorNames: readonly string[];
    readonly evaluations: readonly Evaluation[];
    readonly inputLabel: string;
    readonly evaluableDict: Record<string, unknown>;
}
/** Scorecard for a single dataset evaluation run. */
export interface DatasetScorecard {
    readonly datasetName: string;
    readonly entries: DatasetEntryResult[];
    readonly timestamp: Date;
}
/** Create a DatasetScorecard with default timestamp. */
export declare function createDatasetScorecard(opts: {
    datasetName: string;
    entries: DatasetEntryResult[];
    timestamp?: Date;
}): DatasetScorecard;
/** Render a DatasetScorecard as a self-contained HTML page. */
export declare function generateDatasetScorecardHtml(scorecard: DatasetScorecard, commandArgs: string): string;
/**
 * Generate and save a dataset scorecard HTML to disk.
 *
 * Saves to `{config.root}/scorecards/<timestamp>-<name>.html`.
 *
 * @returns The absolute path of the saved HTML file.
 */
export declare function saveDatasetScorecard(scorecard: DatasetScorecard, commandArgs: string): string;
//# sourceMappingURL=scorecard.d.ts.map