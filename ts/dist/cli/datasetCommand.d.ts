/**
 * `pixie-qa dataset` CLI commands.
 *
 * Provides operations for managing datasets and saving trace spans
 * as evaluable items:
 *
 * - `datasetCreate` — create a new empty dataset.
 * - `datasetList` — list datasets with basic information.
 * - `datasetSave` — select a span from the latest trace and save it.
 */
import type { Dataset } from "../dataset/models";
import { DatasetStore } from "../dataset/store";
import type { JsonValue } from "../storage/evaluable";
import type { Unset } from "../storage/evaluable";
/**
 * Create a new empty dataset.
 */
export declare function datasetCreate(name: string, datasetStore?: DatasetStore): Dataset;
/**
 * Return metadata for every dataset.
 */
export declare function datasetList(datasetStore?: DatasetStore): Array<Record<string, unknown>>;
/**
 * Format dataset metadata rows as an aligned CLI table.
 */
export declare function formatDatasetTable(rows: Array<Record<string, unknown>>): string;
/**
 * Select a span from the latest trace and save it to a dataset.
 */
export declare function datasetSave(opts: {
    name: string;
    select?: string;
    spanName?: string;
    expectedOutput?: JsonValue | Unset;
    notes?: string;
}): Dataset;
//# sourceMappingURL=datasetCommand.d.ts.map