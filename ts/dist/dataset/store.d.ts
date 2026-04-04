/**
 * DatasetStore — JSON-file-backed CRUD for Dataset objects.
 *
 * Each dataset is stored as `<datasetDir>/<slug>.json`.
 * The directory is created on first write if it does not exist.
 */
import type { Evaluable } from "../storage/evaluable";
import type { Dataset } from "./models";
/**
 * Convert a dataset name to a filesystem-safe slug.
 *
 * Lowercase, replace non-alphanumeric runs with `-`, strip leading/trailing `-`.
 */
export declare function _slugify(name: string): string;
export declare class DatasetStore {
    private readonly _dir;
    constructor(datasetDir?: string);
    private _pathFor;
    private _ensureDir;
    private _write;
    private _read;
    /**
     * Create a new dataset.
     * @throws if a dataset with the same name already exists.
     */
    create(name: string, items?: Evaluable[]): Dataset;
    /**
     * Load a dataset by name.
     * @throws if the dataset does not exist.
     */
    get(name: string): Dataset;
    /** Return the names of all stored datasets. */
    list(): string[];
    /** Return metadata for every stored dataset. */
    listDetails(): Array<Record<string, unknown>>;
    /**
     * Delete a dataset by name.
     * @throws if the dataset does not exist.
     */
    delete(name: string): void;
    /** Append items to an existing dataset. */
    append(name: string, ...items: Evaluable[]): Dataset;
    /**
     * Remove an item by index from an existing dataset.
     * @throws if the dataset does not exist or index is out of range.
     */
    remove(name: string, index: number): Dataset;
}
//# sourceMappingURL=store.d.ts.map