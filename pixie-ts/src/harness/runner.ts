/**
 * Evaluation harness for pixie test.
 *
 * Handles dataset loading, evaluator resolution, entry execution, and
 * dataset orchestration with concurrency.
 */

import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

import type { JsonValue, NamedData } from "../eval/evaluable.js";
import { createEvaluable } from "../eval/evaluable.js";
import { evaluate } from "../eval/evaluation.js";
import { AgentEvaluationPending } from "../eval/agentEvaluator.js";
import type { Evaluable } from "../eval/evaluable.js";
import type {
  EvaluationResult,
  PendingEvaluation,
  EntryResult,
} from "./runResult.js";
import { isRunnableClass, type RunnableClass } from "./runnable.js";
import {
  setEvalInput,
  clearEvalInput,
  initEvalOutput,
  getEvalOutput,
  clearEvalOutput,
  runWithWrapContextAsync,
  WrapRegistryMissError,
  WrapTypeMismatchError,
} from "../instrumentation/wrap.js";
import type { WrappedData } from "../instrumentation/wrap.js";
import { INPUT_DATA_KEY } from "../instrumentation/models.js";

// Built-in evaluator names
export const BUILTIN_EVALUATOR_NAMES = new Set([
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

// ---------------------------------------------------------------------------
// Module loading
// ---------------------------------------------------------------------------

async function loadCallable(
  reference: string,
  baseDir: string,
): Promise<unknown> {
  if (!reference.includes(":")) {
    throw new Error(
      `Reference must use filepath:name format, got ${JSON.stringify(reference)}.`,
    );
  }
  const [filePart, attrName] = reference.split(":");
  const filePath = path.resolve(baseDir, filePart);

  if (!fs.existsSync(filePath)) {
    throw new Error(`Module file not found: ${filePath}`);
  }

  const fileUrl = pathToFileURL(filePath).href;
  const mod = (await import(fileUrl)) as Record<string, unknown>;
  const attr = mod[attrName];
  if (attr === undefined) {
    throw new Error(
      `Module ${filePath} does not export ${JSON.stringify(attrName)}`,
    );
  }
  return attr;
}

/** Resolve short built-in name or validate a custom evaluator reference. */
export function resolveEvaluatorName(name: string): string {
  name = name.trim();
  if (name.includes(":")) return name;
  if (BUILTIN_EVALUATOR_NAMES.has(name)) return `pixie.${name}`;
  throw new Error(
    `Unknown evaluator ${JSON.stringify(name)}. ` +
      `Built-in evaluators use bare names (e.g. 'Factuality'). ` +
      `Custom evaluators use filepath:name format.`,
  );
}

/** Import and return an evaluator callable by name. */
async function resolveEvaluator(name: string): Promise<
  (evaluable: Evaluable) => Promise<{
    score: number;
    reasoning: string;
    details: Record<string, unknown>;
  }>
> {
  const fqn = resolveEvaluatorName(name);

  if (fqn.includes(":")) {
    const attr = await loadCallable(fqn, process.cwd());
    if (typeof attr === "function") {
      // Check if it's a zero-arg factory (no required params)
      // We can't easily inspect TS function arity, so call and check
      try {
        const result = attr();
        if (typeof result === "function")
          return result as (evaluable: Evaluable) => Promise<{
            score: number;
            reasoning: string;
            details: Record<string, unknown>;
          }>;
      } catch {
        // Not a factory, use directly
      }
      return attr as (evaluable: Evaluable) => Promise<{
        score: number;
        reasoning: string;
        details: Record<string, unknown>;
      }>;
    }
    throw new TypeError(
      `Evaluator ${JSON.stringify(name)} resolved to non-callable.`,
    );
  }

  // Built-in evaluator from pixie.{Name}
  const shortName = fqn.split(".").pop()!;
  const scorers = await import("../eval/scorers.js");
  const factory = (scorers as Record<string, unknown>)[shortName];
  if (typeof factory !== "function") {
    throw new Error(`Built-in evaluator ${shortName} not found in scorers.`);
  }
  return factory() as (evaluable: Evaluable) => Promise<{
    score: number;
    reasoning: string;
    details: Record<string, unknown>;
  }>;
}

function shortName(name: string): string {
  if (name.includes(":")) return name.split(":").pop()!;
  return name.split(".").pop() ?? name;
}

function expandEvaluatorNames(
  rowEvaluators: string[] | null,
  defaultEvaluators: string[],
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

// ---------------------------------------------------------------------------
// Dataset models
// ---------------------------------------------------------------------------

export interface DatasetEntry {
  readonly inputData: Record<string, JsonValue>;
  readonly evalInput: NamedData[];
  readonly expectation: JsonValue | null;
  readonly evalMetadata: Record<string, JsonValue> | null;
  readonly description: string;
  evaluators: string[];
}

export interface Dataset {
  readonly name: string;
  readonly runnable: string;
  readonly evaluators: string[];
  readonly entries: DatasetEntry[];
}

/** Find all dataset JSON files under path. */
export function discoverDatasetFiles(targetPath: string): string[] {
  const target = path.resolve(targetPath);
  const stat = fs.statSync(target, { throwIfNoEntry: false });
  if (!stat) return [];
  if (stat.isFile() && target.endsWith(".json")) return [target];
  if (stat.isDirectory()) {
    const files: string[] = [];
    function walk(dir: string) {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) walk(full);
        else if (entry.isFile() && entry.name.endsWith(".json"))
          files.push(full);
      }
    }
    walk(target);
    return files.sort();
  }
  return [];
}

/** Load and validate a dataset from a JSON file. */
export function loadDataset(datasetPath: string): Dataset {
  if (!fs.existsSync(datasetPath)) {
    throw new Error(`Dataset not found: ${datasetPath}`);
  }

  const raw = JSON.parse(fs.readFileSync(datasetPath, "utf-8")) as Record<
    string,
    unknown
  >;
  if (typeof raw !== "object" || raw === null || Array.isArray(raw)) {
    throw new Error("Top-level JSON value must be an object.");
  }

  const name = (raw["name"] as string) ?? path.basename(datasetPath, ".json");
  const runnable = raw["runnable"] as string;
  if (!runnable || typeof runnable !== "string") {
    throw new Error("'runnable' must be a non-empty string");
  }

  const defaultEvaluators = Array.isArray(raw["evaluators"])
    ? (raw["evaluators"] as string[])
    : [];

  const rawEntries = raw["entries"] as unknown[];
  if (!Array.isArray(rawEntries) || rawEntries.length === 0) {
    throw new Error("'entries' must be a non-empty array");
  }

  const entries: DatasetEntry[] = rawEntries.map((re, i) => {
    const e = re as Record<string, unknown>;
    const inputData = e["input_data"] as Record<string, JsonValue>;
    if (!inputData || typeof inputData !== "object") {
      throw new Error(`Entry #${i + 1}: input_data must be an object`);
    }
    const desc = e["description"] as string | undefined;
    if (!desc || !desc.trim()) {
      throw new Error(
        `Entry #${i + 1}: description must be a non-empty string`,
      );
    }

    const rowEvals = e["evaluators"] as string[] | undefined;
    const expanded = expandEvaluatorNames(rowEvals ?? null, defaultEvaluators);
    if (expanded.length === 0) {
      throw new Error(
        `Entry #${i + 1}: no evaluators resolved. Set dataset-level or row-level evaluators.`,
      );
    }

    // Validate evaluator names
    for (const eName of expanded) {
      if (eName.trim() !== "...") {
        resolveEvaluatorName(eName);
      }
    }

    const evalInput: NamedData[] = Array.isArray(e["eval_input"])
      ? (e["eval_input"] as Array<{ name: string; value: JsonValue }>).map(
          (nd) => ({
            name: nd.name,
            value: nd.value,
          }),
        )
      : [];

    return {
      inputData,
      evalInput,
      expectation: (e["expectation"] as JsonValue) ?? null,
      evalMetadata: (e["eval_metadata"] as Record<string, JsonValue>) ?? null,
      description: desc,
      evaluators: expanded,
    };
  });

  return { name, runnable, evaluators: defaultEvaluators, entries };
}

/** Resolve a runnable from a filepath:name reference. */
export async function resolveRunnableReference(
  reference: string,
): Promise<unknown> {
  reference = reference.trim();
  if (!reference.includes(":")) {
    throw new Error(
      `Runnable must use filepath:name format, got ${JSON.stringify(reference)}.`,
    );
  }
  return loadCallable(reference, process.cwd());
}

/** Run evaluators on a fully-populated evaluable and return an EntryResult. */
export async function evaluateEntry(
  evaluable: Evaluable,
  evaluatorNames: string[],
): Promise<EntryResult> {
  const evaluators = await Promise.all(
    evaluatorNames.map((n) => resolveEvaluator(n)),
  );
  const shortNames = evaluatorNames.map(shortName);

  const results = await Promise.allSettled(
    evaluators.map(async (ev, i) => {
      try {
        const result = await evaluate(ev, evaluable);
        return {
          evaluator: shortNames[i],
          score: result.score,
          reasoning: result.reasoning,
        } as EvaluationResult;
      } catch (err) {
        if (err instanceof AgentEvaluationPending) {
          return {
            evaluator: err.evaluatorName,
            criteria: err.criteria,
          } as PendingEvaluation;
        }
        throw err;
      }
    }),
  );

  const evalResults: (EvaluationResult | PendingEvaluation)[] = results.map(
    (r, i) => {
      if (r.status === "fulfilled") return r.value;
      const err =
        r.reason instanceof Error ? r.reason.message : String(r.reason);
      return {
        evaluator: shortNames[i],
        score: 0.0,
        reasoning: `Error: ${err}`,
      } as EvaluationResult;
    },
  );

  return {
    evalInput: [...evaluable.evalInput],
    evalOutput: [...evaluable.evalOutput],
    evaluations: evalResults,
    expectation:
      evaluable.expectation === Symbol.for("UNSET")
        ? null
        : (evaluable.expectation as JsonValue),
    evaluators: evaluatorNames,
    evalMetadata: evaluable.evalMetadata,
    description: evaluable.description,
  };
}

/** Process a single dataset entry: call runnable, then evaluate. */
async function runEntry(
  entry: DatasetEntry,
  runnable: (...args: unknown[]) => Promise<unknown>,
  argsSchema: unknown | null,
  entryIndex: number,
): Promise<EntryResult> {
  return runWithWrapContextAsync(async () => {
    initEvalOutput();

    const fullEvalInput: NamedData[] = [
      { name: INPUT_DATA_KEY, value: entry.inputData },
      ...entry.evalInput,
    ];

    const registry = new Map<string, JsonValue>();
    for (const nd of fullEvalInput) {
      registry.set(nd.name, nd.value);
    }
    setEvalInput(registry);

    let runnableResult: unknown;
    try {
      if (argsSchema) {
        const args = entry.inputData;
        runnableResult = await runnable(args);
      } else {
        runnableResult = await runnable(entry.inputData);
      }
    } catch (err) {
      if (
        err instanceof WrapRegistryMissError ||
        err instanceof WrapTypeMismatchError
      ) {
        clearEvalInput();
        clearEvalOutput();
        return {
          evalInput: fullEvalInput,
          evalOutput: [],
          evaluations: [
            {
              evaluator: "WrapError",
              score: 0.0,
              reasoning: err.message,
            },
          ],
          expectation: null,
          evaluators: entry.evaluators,
          evalMetadata: entry.evalMetadata,
          description: entry.description,
        };
      }
      throw err;
    }

    const captured = getEvalOutput() ?? [];
    clearEvalInput();
    clearEvalOutput();

    const wrappedOutput: WrappedData[] = captured.map(
      (raw) => raw as unknown as WrappedData,
    );
    let evalOutput: NamedData[] = wrappedOutput.map((w) => ({
      name: w.name,
      value: w.data,
    }));

    if (evalOutput.length === 0) {
      let fallbackValue: JsonValue;
      try {
        fallbackValue = JSON.parse(JSON.stringify(runnableResult)) as JsonValue;
      } catch {
        fallbackValue = String(runnableResult);
      }
      evalOutput = [{ name: "output", value: fallbackValue }];
    }

    const evaluable = createEvaluable({
      evalInput: fullEvalInput,
      evalOutput,
      expectation: entry.expectation,
      evalMetadata: entry.evalMetadata,
      description: entry.description,
    });

    return evaluateEntry(evaluable, entry.evaluators);
  });
}

/**
 * Run evaluations for a single dataset. Returns [name, runnable, results].
 */
export async function runDataset(
  datasetPath: string,
): Promise<[string, string, EntryResult[]]> {
  const dataset = loadDataset(datasetPath);
  const resolved = await resolveRunnableReference(dataset.runnable);

  const concurrency = 4;
  let running = 0;
  const results: EntryResult[] = new Array(dataset.entries.length);

  if (isRunnableClass(resolved)) {
    const instance = (resolved as RunnableClass).create();
    try {
      await instance.setup();
      const tasks = dataset.entries.map(async (entry, i) => {
        while (running >= concurrency) {
          await new Promise((r) => setTimeout(r, 10));
        }
        running++;
        try {
          results[i] = await runEntry(
            entry,
            instance.run.bind(instance) as (
              ...args: unknown[]
            ) => Promise<unknown>,
            null,
            i,
          );
        } finally {
          running--;
        }
      });
      await Promise.all(tasks);
    } finally {
      await instance.teardown();
    }
  } else {
    const fn = resolved as (...args: unknown[]) => Promise<unknown>;
    const tasks = dataset.entries.map(async (entry, i) => {
      while (running >= concurrency) {
        await new Promise((r) => setTimeout(r, 10));
      }
      running++;
      try {
        results[i] = await runEntry(entry, fn, null, i);
      } finally {
        running--;
      }
    });
    await Promise.all(tasks);
  }

  return [dataset.name, dataset.runnable, results];
}
