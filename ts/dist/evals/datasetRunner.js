"use strict";
/**
 * Dataset-driven test runner for `pixie test`.
 *
 * Processes dataset JSON files where each row specifies its own evaluators.
 * Built-in evaluator names (no dots) are auto-resolved to `pixie-qa.{Name}`.
 * Custom evaluators use fully qualified names.
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.BUILTIN_EVALUATOR_NAMES = void 0;
exports.resolveEvaluatorName = resolveEvaluatorName;
exports.listAvailableEvaluators = listAvailableEvaluators;
exports.discoverDatasetFiles = discoverDatasetFiles;
exports.validateDatasetFile = validateDatasetFile;
exports.loadDatasetEntries = loadDatasetEntries;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const evaluable_1 = require("../storage/evaluable");
// ── Constants ────────────────────────────────────────────────────────────────
/** Names of all built-in evaluators. */
exports.BUILTIN_EVALUATOR_NAMES = new Set([
    "LevenshteinMatch",
    "ExactMatch",
    "NumericDiff",
    "JSONDiff",
    "ValidJSON",
    "ListContains",
    "EmbeddingSimilarity",
    "Factuality",
    "ClosedQA",
    "Battle",
    "Humor",
    "Security",
    "Sql",
    "Summary",
    "Translation",
    "Possible",
    "Moderation",
    "ContextRelevancy",
    "Faithfulness",
    "AnswerRelevancy",
    "AnswerCorrectness",
]);
// ── Functions ────────────────────────────────────────────────────────────────
/**
 * Resolve short built-in name to fully qualified, or pass through FQN.
 *
 * @throws if name has no dots and is not a known built-in.
 */
function resolveEvaluatorName(name) {
    const trimmed = name.trim();
    if (trimmed.includes("."))
        return trimmed;
    if (exports.BUILTIN_EVALUATOR_NAMES.has(trimmed)) {
        return `pixie-qa.${trimmed}`;
    }
    throw new Error(`Unknown evaluator ${JSON.stringify(trimmed)}. ` +
        `Use a fully qualified name for custom evaluators ` +
        `(e.g. 'myapp.evals.${trimmed}').`);
}
/**
 * Import and instantiate an evaluator by name.
 */
function resolveEvaluator(name) {
    const fqn = resolveEvaluatorName(name);
    const lastDot = fqn.lastIndexOf(".");
    const modulePath = fqn.substring(0, lastDot);
    const className = fqn.substring(lastDot + 1);
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const mod = require(modulePath);
    const cls = mod[className];
    if (typeof cls === "function") {
        return cls();
    }
    return cls;
}
/**
 * Import a runnable function by fully qualified name.
 */
function resolveRunnable(fqn) {
    const lastDot = fqn.lastIndexOf(".");
    if (lastDot === -1) {
        throw new Error(`Runnable must be a fully qualified name (e.g. 'myapp.module.func'), ` +
            `got ${JSON.stringify(fqn)}.`);
    }
    const modulePath = fqn.substring(0, lastDot);
    const funcName = fqn.substring(lastDot + 1);
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const mod = require(modulePath);
    return mod[funcName];
}
/** Extract the class name from a possibly fully qualified name. */
function shortName(name) {
    const lastDot = name.lastIndexOf(".");
    return lastDot === -1 ? name : name.substring(lastDot + 1);
}
/**
 * Resolve row-level evaluator names against defaults.
 *
 * - If `rowEvaluators` is null or empty, use `defaultEvaluators`.
 * - `"..."` in the row list is replaced with all `defaultEvaluators`.
 */
function expandEvaluatorNames(rowEvaluators, defaultEvaluators) {
    if (!rowEvaluators || rowEvaluators.length === 0) {
        return [...defaultEvaluators];
    }
    const result = [];
    for (const name of rowEvaluators) {
        if (name.trim() === "...") {
            result.push(...defaultEvaluators);
        }
        else {
            result.push(name);
        }
    }
    return result;
}
/** Return sorted list of all built-in evaluator names. */
function listAvailableEvaluators() {
    return [...exports.BUILTIN_EVALUATOR_NAMES].sort();
}
/**
 * Find all dataset JSON files under `searchPath`.
 *
 * Handles file, directory, or `.` for current dir.
 */
function discoverDatasetFiles(searchPath) {
    const target = path_1.default.resolve(searchPath);
    const stat = fs_1.default.statSync(target, { throwIfNoEntry: false });
    if (stat?.isFile() && target.endsWith(".json")) {
        return [target];
    }
    if (stat?.isDirectory()) {
        return findJsonFiles(target).sort();
    }
    return [];
}
function findJsonFiles(dir) {
    const results = [];
    const entries = fs_1.default.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
        const fullPath = path_1.default.join(dir, entry.name);
        if (entry.isDirectory()) {
            results.push(...findJsonFiles(fullPath));
        }
        else if (entry.isFile() && entry.name.endsWith(".json")) {
            results.push(fullPath);
        }
    }
    return results;
}
// ── Validation helpers ───────────────────────────────────────────────────────
function parseEvaluatorList(raw, opts) {
    if (!Array.isArray(raw)) {
        opts.errors.push(`${opts.location}: 'evaluators' must be a list of strings.`);
        return [];
    }
    const names = [];
    for (let i = 0; i < raw.length; i++) {
        const value = raw[i];
        if (typeof value !== "string" || !value.trim()) {
            opts.errors.push(`${opts.location}: evaluator #${i + 1} must be a non-empty string.`);
            continue;
        }
        const name = value.trim();
        if (name === "..." && !opts.allowEllipsis) {
            opts.errors.push(`${opts.location}: '...' is only allowed in row-level evaluators.`);
            continue;
        }
        names.push(name);
    }
    return names;
}
function validateEvaluatorNames(names, opts) {
    for (const name of names) {
        try {
            resolveEvaluatorName(name);
            resolveEvaluator(name);
        }
        catch (exc) {
            const error = exc;
            opts.errors.push(`${opts.location}: invalid evaluator ${JSON.stringify(name)} (${error.name}: ${error.message}).`);
        }
    }
}
/**
 * Validate a dataset file and return a list of human-readable errors.
 * Empty list means the file is valid.
 */
function validateDatasetFile(datasetPath) {
    if (!fs_1.default.existsSync(datasetPath)) {
        return [`${datasetPath}: dataset not found.`];
    }
    let data;
    try {
        const raw = fs_1.default.readFileSync(datasetPath, "utf-8");
        data = JSON.parse(raw);
    }
    catch (exc) {
        const error = exc;
        return [`${datasetPath}: invalid JSON (${error.message}).`];
    }
    if (typeof data !== "object" || data === null || Array.isArray(data)) {
        return [`${datasetPath}: top-level JSON value must be an object.`];
    }
    const errors = [];
    const obj = data;
    const runnableRaw = obj["runnable"];
    if (typeof runnableRaw !== "string" || !runnableRaw.trim()) {
        errors.push(`${datasetPath}: missing required top-level 'runnable' (non-empty string).`);
    }
    else {
        const runnable = runnableRaw.trim();
        try {
            const resolved = resolveRunnable(runnable);
            if (typeof resolved !== "function") {
                errors.push(`${datasetPath}: runnable ${JSON.stringify(runnable)} does not resolve to a callable.`);
            }
        }
        catch (exc) {
            const error = exc;
            errors.push(`${datasetPath}: invalid runnable ${JSON.stringify(runnable)} (${error.name}: ${error.message}).`);
        }
    }
    const defaultEvaluatorsRaw = obj["evaluators"] ?? [];
    const defaultEvaluators = parseEvaluatorList(defaultEvaluatorsRaw, {
        allowEllipsis: false,
        location: `${datasetPath} (dataset defaults)`,
        errors,
    });
    validateEvaluatorNames(defaultEvaluators, {
        location: `${datasetPath} (dataset defaults)`,
        errors,
    });
    const itemsRaw = obj["items"] ?? [];
    if (!Array.isArray(itemsRaw)) {
        errors.push(`${datasetPath}: 'items' must be a list.`);
        return errors;
    }
    for (let idx = 0; idx < itemsRaw.length; idx++) {
        const row = itemsRaw[idx];
        const rowLocation = `${datasetPath} item #${idx + 1}`;
        if (typeof row !== "object" || row === null || Array.isArray(row)) {
            errors.push(`${rowLocation}: item must be an object.`);
            continue;
        }
        const rowObj = row;
        const description = rowObj["description"];
        if (typeof description !== "string" || !description.trim()) {
            errors.push(`${rowLocation}: missing required 'description' (non-empty string).`);
        }
        let rowEvaluators = null;
        if ("evaluators" in rowObj) {
            rowEvaluators = parseEvaluatorList(rowObj["evaluators"], {
                allowEllipsis: true,
                location: rowLocation,
                errors,
            });
        }
        let resolvedEvaluators = expandEvaluatorNames(rowEvaluators, defaultEvaluators);
        resolvedEvaluators = resolvedEvaluators
            .map((n) => n.trim())
            .filter((n) => n.length > 0);
        if (resolvedEvaluators.length === 0) {
            errors.push(`${rowLocation}: no evaluators resolved. ` +
                "Set dataset-level 'evaluators' or row-level 'evaluators'.");
            continue;
        }
        validateEvaluatorNames(resolvedEvaluators.filter((n) => n !== "..."), { location: rowLocation, errors });
    }
    return errors;
}
/**
 * Load a dataset and return a LoadedDataset.
 *
 * @throws if the file does not exist or validation fails.
 */
function loadDatasetEntries(datasetPath) {
    if (!fs_1.default.existsSync(datasetPath)) {
        throw new Error(`Dataset not found: ${datasetPath}`);
    }
    const validationErrors = validateDatasetFile(datasetPath);
    if (validationErrors.length > 0) {
        const message = "Dataset validation failed:\n" + validationErrors.join("\n");
        throw new Error(message);
    }
    const raw = JSON.parse(fs_1.default.readFileSync(datasetPath, "utf-8"));
    const datasetName = raw["name"] ?? path_1.default.basename(datasetPath, ".json");
    const runnable = String(raw["runnable"]).trim();
    const defaultEvaluatorsRaw = (raw["evaluators"] ?? []);
    const defaultEvaluators = defaultEvaluatorsRaw
        .filter((n) => typeof n === "string" && n.trim().length > 0)
        .map((n) => n.trim());
    const rawItems = (raw["items"] ?? []);
    const entries = [];
    for (const itemData of rawItems) {
        const rowEvaluatorsRaw = itemData["evaluators"];
        let rowEvaluators = null;
        if (Array.isArray(rowEvaluatorsRaw)) {
            rowEvaluators = rowEvaluatorsRaw.filter((n) => typeof n === "string");
        }
        let evaluatorNames = expandEvaluatorNames(rowEvaluators, defaultEvaluators);
        evaluatorNames = evaluatorNames
            .map((n) => n.trim())
            .filter((n) => n.length > 0);
        const evaluable = {
            evalInput: (itemData["evalInput"] ?? itemData["eval_input"] ?? null),
            evalOutput: (itemData["evalOutput"] ?? itemData["eval_output"] ?? null),
            evalMetadata: (itemData["evalMetadata"] ??
                itemData["eval_metadata"] ??
                null),
            expectedOutput: itemData["expectedOutput"] !== undefined
                ? itemData["expectedOutput"]
                : itemData["expected_output"] !== undefined
                    ? itemData["expected_output"]
                    : evaluable_1.UNSET,
            evaluators: itemData["evaluators"] ?? null,
            description: itemData["description"] ?? null,
        };
        entries.push([evaluable, evaluatorNames]);
    }
    return {
        name: datasetName,
        runnable,
        entries,
    };
}
//# sourceMappingURL=datasetRunner.js.map