"use strict";
/**
 * DatasetStore — JSON-file-backed CRUD for Dataset objects.
 *
 * Each dataset is stored as `<datasetDir>/<slug>.json`.
 * The directory is created on first write if it does not exist.
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.DatasetStore = void 0;
exports._slugify = _slugify;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const config_1 = require("../config");
const evaluable_1 = require("../storage/evaluable");
// ── Helpers ──────────────────────────────────────────────────────────────────
/**
 * Convert a dataset name to a filesystem-safe slug.
 *
 * Lowercase, replace non-alphanumeric runs with `-`, strip leading/trailing `-`.
 */
function _slugify(name) {
    const slug = name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
    if (!slug) {
        throw new Error(`Cannot slugify empty or non-alphanumeric name: ${JSON.stringify(name)}`);
    }
    return slug;
}
function timestampToIso(ts) {
    const d = new Date(ts);
    // Format: YYYY-MM-DD HH:MM:SS
    return d.toISOString().replace("T", " ").replace(/\.\d{3}Z$/, "");
}
// ── Serialization helpers ────────────────────────────────────────────────────
function evaluableToJson(ev) {
    const obj = {
        evalInput: ev.evalInput,
        evalOutput: ev.evalOutput,
        evalMetadata: ev.evalMetadata,
        expectedOutput: ev.expectedOutput === evaluable_1.UNSET ? null : ev.expectedOutput,
        evaluators: ev.evaluators,
        description: ev.description,
    };
    return obj;
}
function jsonToEvaluable(raw) {
    return {
        evalInput: (raw["evalInput"] ?? raw["eval_input"] ?? null),
        evalOutput: (raw["evalOutput"] ?? raw["eval_output"] ?? null),
        evalMetadata: (raw["evalMetadata"] ??
            raw["eval_metadata"] ??
            null),
        expectedOutput: raw["expectedOutput"] !== undefined
            ? raw["expectedOutput"]
            : raw["expected_output"] !== undefined
                ? raw["expected_output"]
                : evaluable_1.UNSET,
        evaluators: raw["evaluators"] ?? null,
        description: raw["description"] ?? null,
    };
}
// ── DatasetStore ─────────────────────────────────────────────────────────────
class DatasetStore {
    _dir;
    constructor(datasetDir) {
        this._dir = datasetDir ?? (0, config_1.getConfig)().datasetDir;
    }
    _pathFor(name) {
        return path_1.default.join(this._dir, `${_slugify(name)}.json`);
    }
    _ensureDir() {
        fs_1.default.mkdirSync(this._dir, { recursive: true });
    }
    _write(filePath, dataset) {
        this._ensureDir();
        const data = {
            name: dataset.name,
            items: dataset.items.map(evaluableToJson),
        };
        fs_1.default.writeFileSync(filePath, JSON.stringify(data, null, 2) + "\n", "utf-8");
    }
    _read(filePath) {
        const raw = JSON.parse(fs_1.default.readFileSync(filePath, "utf-8"));
        return {
            name: raw.name,
            items: raw.items.map(jsonToEvaluable),
        };
    }
    // ── CRUD ──────────────────────────────────────────────────────────────
    /**
     * Create a new dataset.
     * @throws if a dataset with the same name already exists.
     */
    create(name, items) {
        const filePath = this._pathFor(name);
        if (fs_1.default.existsSync(filePath)) {
            throw new Error(`Dataset already exists: ${JSON.stringify(name)}`);
        }
        const dataset = { name, items: items ?? [] };
        this._write(filePath, dataset);
        return dataset;
    }
    /**
     * Load a dataset by name.
     * @throws if the dataset does not exist.
     */
    get(name) {
        const filePath = this._pathFor(name);
        if (!fs_1.default.existsSync(filePath)) {
            throw new Error(`Dataset not found: ${JSON.stringify(name)}`);
        }
        return this._read(filePath);
    }
    /** Return the names of all stored datasets. */
    list() {
        if (!fs_1.default.existsSync(this._dir))
            return [];
        const names = [];
        const files = fs_1.default.readdirSync(this._dir).filter((f) => f.endsWith(".json")).sort();
        for (const f of files) {
            try {
                const ds = this._read(path_1.default.join(this._dir, f));
                names.push(ds.name);
            }
            catch {
                continue; // skip malformed files
            }
        }
        return names;
    }
    /** Return metadata for every stored dataset. */
    listDetails() {
        if (!fs_1.default.existsSync(this._dir))
            return [];
        const rows = [];
        const files = fs_1.default.readdirSync(this._dir).filter((f) => f.endsWith(".json")).sort();
        for (const f of files) {
            try {
                const filePath = path_1.default.join(this._dir, f);
                const ds = this._read(filePath);
                const stat = fs_1.default.statSync(filePath);
                rows.push({
                    name: ds.name,
                    rowCount: ds.items.length,
                    createdAt: timestampToIso(stat.birthtimeMs),
                    updatedAt: timestampToIso(stat.mtimeMs),
                });
            }
            catch {
                continue; // skip malformed files
            }
        }
        return rows;
    }
    /**
     * Delete a dataset by name.
     * @throws if the dataset does not exist.
     */
    delete(name) {
        const filePath = this._pathFor(name);
        if (!fs_1.default.existsSync(filePath)) {
            throw new Error(`Dataset not found: ${JSON.stringify(name)}`);
        }
        fs_1.default.unlinkSync(filePath);
    }
    /** Append items to an existing dataset. */
    append(name, ...items) {
        const dataset = this.get(name);
        const updated = {
            name: dataset.name,
            items: [...dataset.items, ...items],
        };
        this._write(this._pathFor(name), updated);
        return updated;
    }
    /**
     * Remove an item by index from an existing dataset.
     * @throws if the dataset does not exist or index is out of range.
     */
    remove(name, index) {
        const dataset = this.get(name);
        const items = [...dataset.items];
        if (index < 0 || index >= items.length) {
            throw new RangeError(`Index ${index} out of range for dataset ${JSON.stringify(name)} with ${items.length} items`);
        }
        items.splice(index, 1);
        const updated = { name: dataset.name, items };
        this._write(this._pathFor(name), updated);
        return updated;
    }
}
exports.DatasetStore = DatasetStore;
//# sourceMappingURL=store.js.map