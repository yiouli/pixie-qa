/**
 * Dataset-driven test runner for `pixie test`.
 *
 * Processes dataset JSON files where each row specifies its own evaluators.
 * Built-in evaluator names (no dots) are auto-resolved to `pixie-qa.{Name}`.
 * Custom evaluators use fully qualified names.
 */

import fs from "fs";
import path from "path";

import type { Evaluable, JsonValue } from "../storage/evaluable";
import { UNSET } from "../storage/evaluable";

// ── Constants ────────────────────────────────────────────────────────────────

/** Names of all built-in evaluators. */
export const BUILTIN_EVALUATOR_NAMES: ReadonlySet<string> = new Set([
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

// ── Types ────────────────────────────────────────────────────────────────────

/** Parsed dataset ready for evaluation. */
export interface LoadedDataset {
  readonly name: string;
  /** Fully qualified name of the runnable function. */
  readonly runnable: string;
  /** List of [evaluable, evaluatorNames] pairs. */
  readonly entries: Array<[Evaluable, string[]]>;
}

// ── Functions ────────────────────────────────────────────────────────────────

/**
 * Resolve short built-in name to fully qualified, or pass through FQN.
 *
 * @throws if name has no dots and is not a known built-in.
 */
export function resolveEvaluatorName(name: string): string {
  const trimmed = name.trim();
  if (trimmed.includes(".")) return trimmed;
  if (BUILTIN_EVALUATOR_NAMES.has(trimmed)) {
    return `pixie-qa.${trimmed}`;
  }
  throw new Error(
    `Unknown evaluator ${JSON.stringify(trimmed)}. ` +
      `Use a fully qualified name for custom evaluators ` +
      `(e.g. 'myapp.evals.${trimmed}').`
  );
}

/**
 * Import and instantiate an evaluator by name.
 */
function resolveEvaluator(name: string): unknown {
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
function resolveRunnable(fqn: string): unknown {
  const lastDot = fqn.lastIndexOf(".");
  if (lastDot === -1) {
    throw new Error(
      `Runnable must be a fully qualified name (e.g. 'myapp.module.func'), ` +
        `got ${JSON.stringify(fqn)}.`
    );
  }
  const modulePath = fqn.substring(0, lastDot);
  const funcName = fqn.substring(lastDot + 1);

  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const mod = require(modulePath);
  return mod[funcName];
}

/** Extract the class name from a possibly fully qualified name. */
function shortName(name: string): string {
  const lastDot = name.lastIndexOf(".");
  return lastDot === -1 ? name : name.substring(lastDot + 1);
}

/**
 * Resolve row-level evaluator names against defaults.
 *
 * - If `rowEvaluators` is null or empty, use `defaultEvaluators`.
 * - `"..."` in the row list is replaced with all `defaultEvaluators`.
 */
function expandEvaluatorNames(
  rowEvaluators: string[] | null,
  defaultEvaluators: string[]
): string[] {
  if (!rowEvaluators || rowEvaluators.length === 0) {
    return [...defaultEvaluators];
  }

  const result: string[] = [];
  for (const name of rowEvaluators) {
    if (name.trim() === "...") {
      result.push(...defaultEvaluators);
    } else {
      result.push(name);
    }
  }
  return result;
}

/** Return sorted list of all built-in evaluator names. */
export function listAvailableEvaluators(): string[] {
  return [...BUILTIN_EVALUATOR_NAMES].sort();
}

/**
 * Find all dataset JSON files under `searchPath`.
 *
 * Handles file, directory, or `.` for current dir.
 */
export function discoverDatasetFiles(searchPath: string): string[] {
  const target = path.resolve(searchPath);
  const stat = fs.statSync(target, { throwIfNoEntry: false });

  if (stat?.isFile() && target.endsWith(".json")) {
    return [target];
  }

  if (stat?.isDirectory()) {
    return findJsonFiles(target).sort();
  }

  return [];
}

function findJsonFiles(dir: string): string[] {
  const results: string[] = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...findJsonFiles(fullPath));
    } else if (entry.isFile() && entry.name.endsWith(".json")) {
      results.push(fullPath);
    }
  }
  return results;
}

// ── Validation helpers ───────────────────────────────────────────────────────

function parseEvaluatorList(
  raw: unknown,
  opts: {
    allowEllipsis: boolean;
    location: string;
    errors: string[];
  }
): string[] {
  if (!Array.isArray(raw)) {
    opts.errors.push(
      `${opts.location}: 'evaluators' must be a list of strings.`
    );
    return [];
  }

  const names: string[] = [];
  for (let i = 0; i < raw.length; i++) {
    const value = raw[i];
    if (typeof value !== "string" || !value.trim()) {
      opts.errors.push(
        `${opts.location}: evaluator #${i + 1} must be a non-empty string.`
      );
      continue;
    }
    const name = value.trim();
    if (name === "..." && !opts.allowEllipsis) {
      opts.errors.push(
        `${opts.location}: '...' is only allowed in row-level evaluators.`
      );
      continue;
    }
    names.push(name);
  }
  return names;
}

function validateEvaluatorNames(
  names: string[],
  opts: { location: string; errors: string[] }
): void {
  for (const name of names) {
    try {
      resolveEvaluatorName(name);
      resolveEvaluator(name);
    } catch (exc) {
      const error = exc as Error;
      opts.errors.push(
        `${opts.location}: invalid evaluator ${JSON.stringify(name)} (${error.name}: ${error.message}).`
      );
    }
  }
}

/**
 * Validate a dataset file and return a list of human-readable errors.
 * Empty list means the file is valid.
 */
export function validateDatasetFile(datasetPath: string): string[] {
  if (!fs.existsSync(datasetPath)) {
    return [`${datasetPath}: dataset not found.`];
  }

  let data: unknown;
  try {
    const raw = fs.readFileSync(datasetPath, "utf-8");
    data = JSON.parse(raw);
  } catch (exc) {
    const error = exc as SyntaxError;
    return [`${datasetPath}: invalid JSON (${error.message}).`];
  }

  if (typeof data !== "object" || data === null || Array.isArray(data)) {
    return [`${datasetPath}: top-level JSON value must be an object.`];
  }

  const errors: string[] = [];
  const obj = data as Record<string, unknown>;

  const runnableRaw = obj["runnable"];
  if (typeof runnableRaw !== "string" || !runnableRaw.trim()) {
    errors.push(
      `${datasetPath}: missing required top-level 'runnable' (non-empty string).`
    );
  } else {
    const runnable = runnableRaw.trim();
    try {
      const resolved = resolveRunnable(runnable);
      if (typeof resolved !== "function") {
        errors.push(
          `${datasetPath}: runnable ${JSON.stringify(runnable)} does not resolve to a callable.`
        );
      }
    } catch (exc) {
      const error = exc as Error;
      errors.push(
        `${datasetPath}: invalid runnable ${JSON.stringify(runnable)} (${error.name}: ${error.message}).`
      );
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

    const rowObj = row as Record<string, unknown>;
    const description = rowObj["description"];
    if (typeof description !== "string" || !description.trim()) {
      errors.push(
        `${rowLocation}: missing required 'description' (non-empty string).`
      );
    }

    let rowEvaluators: string[] | null = null;
    if ("evaluators" in rowObj) {
      rowEvaluators = parseEvaluatorList(rowObj["evaluators"], {
        allowEllipsis: true,
        location: rowLocation,
        errors,
      });
    }

    let resolvedEvaluators = expandEvaluatorNames(
      rowEvaluators,
      defaultEvaluators
    );
    resolvedEvaluators = resolvedEvaluators
      .map((n) => n.trim())
      .filter((n) => n.length > 0);

    if (resolvedEvaluators.length === 0) {
      errors.push(
        `${rowLocation}: no evaluators resolved. ` +
          "Set dataset-level 'evaluators' or row-level 'evaluators'."
      );
      continue;
    }

    validateEvaluatorNames(
      resolvedEvaluators.filter((n) => n !== "..."),
      { location: rowLocation, errors }
    );
  }

  return errors;
}

/**
 * Load a dataset and return a LoadedDataset.
 *
 * @throws if the file does not exist or validation fails.
 */
export function loadDatasetEntries(datasetPath: string): LoadedDataset {
  if (!fs.existsSync(datasetPath)) {
    throw new Error(`Dataset not found: ${datasetPath}`);
  }

  const validationErrors = validateDatasetFile(datasetPath);
  if (validationErrors.length > 0) {
    const message =
      "Dataset validation failed:\n" + validationErrors.join("\n");
    throw new Error(message);
  }

  const raw = JSON.parse(fs.readFileSync(datasetPath, "utf-8")) as Record<
    string,
    unknown
  >;
  const datasetName = (raw["name"] as string) ?? path.basename(datasetPath, ".json");
  const runnable = String(raw["runnable"]).trim();
  const defaultEvaluatorsRaw = (raw["evaluators"] ?? []) as unknown[];
  const defaultEvaluators = defaultEvaluatorsRaw
    .filter((n): n is string => typeof n === "string" && n.trim().length > 0)
    .map((n) => n.trim());

  const rawItems = (raw["items"] ?? []) as Array<Record<string, unknown>>;

  const entries: Array<[Evaluable, string[]]> = [];
  for (const itemData of rawItems) {
    const rowEvaluatorsRaw = itemData["evaluators"];
    let rowEvaluators: string[] | null = null;
    if (Array.isArray(rowEvaluatorsRaw)) {
      rowEvaluators = rowEvaluatorsRaw.filter(
        (n): n is string => typeof n === "string"
      );
    }

    let evaluatorNames = expandEvaluatorNames(
      rowEvaluators,
      defaultEvaluators
    );
    evaluatorNames = evaluatorNames
      .map((n) => n.trim())
      .filter((n) => n.length > 0);

    const evaluable: Evaluable = {
      evalInput: (itemData["evalInput"] ?? itemData["eval_input"] ?? null) as JsonValue,
      evalOutput: (itemData["evalOutput"] ?? itemData["eval_output"] ?? null) as JsonValue,
      evalMetadata:
        (itemData["evalMetadata"] ??
          itemData["eval_metadata"] ??
          null) as Record<string, JsonValue> | null,
      expectedOutput:
        itemData["expectedOutput"] !== undefined
          ? (itemData["expectedOutput"] as JsonValue)
          : itemData["expected_output"] !== undefined
            ? (itemData["expected_output"] as JsonValue)
            : UNSET,
      evaluators: (itemData["evaluators"] as readonly string[]) ?? null,
      description: (itemData["description"] as string) ?? null,
    };

    entries.push([evaluable, evaluatorNames]);
  }

  return {
    name: datasetName,
    runnable,
    entries,
  };
}
