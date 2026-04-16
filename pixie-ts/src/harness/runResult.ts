/**
 * Test result models and persistence for pixie test.
 */

import fs from "node:fs";
import path from "node:path";
import type { JsonValue, NamedData } from "../eval/evaluable.js";
import { collapseNamedData } from "../eval/evaluable.js";
import { getConfig } from "../config.js";

/** Generate a timestamped test run ID. */
export function generateTestId(): string {
  const now = new Date();
  const pad2 = (n: number) => n.toString().padStart(2, "0");
  return `${now.getUTCFullYear()}${pad2(now.getUTCMonth() + 1)}${pad2(now.getUTCDate())}-${pad2(now.getUTCHours())}${pad2(now.getUTCMinutes())}${pad2(now.getUTCSeconds())}`;
}

/** Result of a single evaluator on a single entry. */
export interface EvaluationResult {
  readonly evaluator: string;
  readonly score: number;
  readonly reasoning: string;
}

/** An evaluation awaiting agent grading. */
export interface PendingEvaluation {
  readonly evaluator: string;
  readonly criteria: string;
}

export function isEvaluationResult(
  ev: EvaluationResult | PendingEvaluation,
): ev is EvaluationResult {
  return "score" in ev;
}

/** Results for a single dataset entry. */
export interface EntryResult {
  readonly evalInput: NamedData[];
  readonly evalOutput: NamedData[];
  readonly evaluations: ReadonlyArray<EvaluationResult | PendingEvaluation>;
  readonly expectation: JsonValue | null;
  readonly evaluators: string[];
  readonly evalMetadata: Record<string, JsonValue> | null;
  readonly description: string | null;
  readonly traceFile?: string | null;
  readonly analysis?: string | null;
}

/** Convenience: collapsed input for display. */
export function entryInput(entry: EntryResult): JsonValue {
  return collapseNamedData(entry.evalInput);
}

/** Convenience: collapsed output for display. */
export function entryOutput(entry: EntryResult): JsonValue {
  return collapseNamedData(entry.evalOutput);
}

/** Results for a single dataset evaluation run. */
export interface DatasetResult {
  readonly dataset: string;
  readonly datasetPath: string;
  readonly runnable: string;
  readonly entries: EntryResult[];
  analysis?: string | null;
}

/** Top-level test run result container. */
export interface RunResult {
  readonly testId: string;
  readonly command: string;
  readonly startedAt: string;
  readonly endedAt: string;
  datasets: DatasetResult[];
}

// ---------------------------------------------------------------------------
// Serialization helpers
// ---------------------------------------------------------------------------

function evalToDict(
  ev: EvaluationResult | PendingEvaluation,
): Record<string, unknown> {
  if ("criteria" in ev && !("score" in ev)) {
    return {
      evaluator: ev.evaluator,
      status: "pending",
      criteria: ev.criteria,
    };
  }
  const e = ev as EvaluationResult;
  return { evaluator: e.evaluator, score: e.score, reasoning: e.reasoning };
}

function entryToDict(entry: EntryResult): Record<string, unknown> {
  const evalDicts = entry.evaluations.map(evalToDict);
  const d: Record<string, unknown> = {
    input: entryInput(entry),
    output: entryOutput(entry),
    evaluations: evalDicts,
  };
  if (entry.expectation !== null) d["expectedOutput"] = entry.expectation;
  if (entry.description !== null) d["description"] = entry.description;
  if (entry.traceFile) d["traceFile"] = entry.traceFile;
  if (entry.analysis) d["analysis"] = entry.analysis;
  return d;
}

// ---------------------------------------------------------------------------
// JSONL helpers
// ---------------------------------------------------------------------------

function writeJsonl(filePath: string, items: Record<string, unknown>[]): void {
  const lines = items.map((item) => JSON.stringify(item)).join("\n") + "\n";
  fs.writeFileSync(filePath, lines, "utf-8");
}

function readJsonl(filePath: string): Record<string, unknown>[] {
  if (!fs.existsSync(filePath)) return [];
  const text = fs.readFileSync(filePath, "utf-8");
  return text
    .split("\n")
    .filter((line) => line.trim())
    .map((line) => JSON.parse(line) as Record<string, unknown>);
}

// ---------------------------------------------------------------------------
// Save / Load
// ---------------------------------------------------------------------------

/** Write test result artifacts to the per-entry directory structure. */
export function saveTestResult(result: RunResult): string {
  const config = getConfig();
  const resultDir = path.join(config.root, "results", result.testId);
  fs.mkdirSync(resultDir, { recursive: true });

  // meta.json
  const meta = {
    testId: result.testId,
    command: result.command,
    startedAt: result.startedAt,
    endedAt: result.endedAt,
  };
  fs.writeFileSync(
    path.join(resultDir, "meta.json"),
    JSON.stringify(meta, null, 2),
    "utf-8",
  );

  for (let dsIdx = 0; dsIdx < result.datasets.length; dsIdx++) {
    const ds = result.datasets[dsIdx];
    const dsDir = path.join(resultDir, `dataset-${dsIdx}`);
    fs.mkdirSync(dsDir, { recursive: true });

    // metadata.json
    const dsMeta = {
      dataset: ds.dataset,
      datasetPath: ds.datasetPath,
      runnable: ds.runnable,
    };
    fs.writeFileSync(
      path.join(dsDir, "metadata.json"),
      JSON.stringify(dsMeta, null, 2),
      "utf-8",
    );

    for (let entryIdx = 0; entryIdx < ds.entries.length; entryIdx++) {
      const entry = ds.entries[entryIdx];
      const entryDir = path.join(dsDir, `entry-${entryIdx}`);
      fs.mkdirSync(entryDir, { recursive: true });

      // config.json
      const configData: Record<string, unknown> = {
        evaluators: entry.evaluators,
      };
      if (entry.description !== null)
        configData["description"] = entry.description;
      if (entry.expectation !== null)
        configData["expectation"] = entry.expectation;
      if (entry.evalMetadata !== null)
        configData["evalMetadata"] = entry.evalMetadata;
      fs.writeFileSync(
        path.join(entryDir, "config.json"),
        JSON.stringify(configData, null, 2),
        "utf-8",
      );

      // eval-input.jsonl
      writeJsonl(
        path.join(entryDir, "eval-input.jsonl"),
        entry.evalInput.map((nd) => ({ name: nd.name, value: nd.value })),
      );

      // eval-output.jsonl
      writeJsonl(
        path.join(entryDir, "eval-output.jsonl"),
        entry.evalOutput.map((nd) => ({ name: nd.name, value: nd.value })),
      );

      // evaluations.jsonl
      writeJsonl(
        path.join(entryDir, "evaluations.jsonl"),
        entry.evaluations.map(evalToDict),
      );
    }
  }

  return path.resolve(resultDir);
}

/** Load a test result from the per-entry directory structure. */
export function loadTestResult(testId: string): RunResult {
  const config = getConfig();
  const resultDir = path.join(config.root, "results", testId);
  const metaPath = path.join(resultDir, "meta.json");
  const meta = JSON.parse(fs.readFileSync(metaPath, "utf-8")) as Record<
    string,
    unknown
  >;

  const datasets: DatasetResult[] = [];
  let dsIdx = 0;
  while (true) {
    const dsDir = path.join(resultDir, `dataset-${dsIdx}`);
    if (!fs.existsSync(dsDir)) break;

    const dsMeta = JSON.parse(
      fs.readFileSync(path.join(dsDir, "metadata.json"), "utf-8"),
    ) as Record<string, unknown>;

    const entries: EntryResult[] = [];
    let entryIdx = 0;
    while (true) {
      const entryDir = path.join(dsDir, `entry-${entryIdx}`);
      if (!fs.existsSync(entryDir)) break;

      const entryConfig = JSON.parse(
        fs.readFileSync(path.join(entryDir, "config.json"), "utf-8"),
      ) as Record<string, unknown>;

      const rawInput = readJsonl(path.join(entryDir, "eval-input.jsonl"));
      const evalInput = rawInput.map((item) => ({
        name: item["name"] as string,
        value: item["value"] as JsonValue,
      }));

      const rawOutput = readJsonl(path.join(entryDir, "eval-output.jsonl"));
      const evalOutput = rawOutput.map((item) => ({
        name: item["name"] as string,
        value: item["value"] as JsonValue,
      }));

      const rawEvals = readJsonl(path.join(entryDir, "evaluations.jsonl"));
      const evaluations: Array<EvaluationResult | PendingEvaluation> =
        rawEvals.map((ev) => {
          if (ev["status"] === "pending") {
            return {
              evaluator: ev["evaluator"] as string,
              criteria: (ev["criteria"] as string) ?? "",
            };
          }
          return {
            evaluator: ev["evaluator"] as string,
            score: ev["score"] as number,
            reasoning: ev["reasoning"] as string,
          };
        });

      let traceFile: string | null = null;
      const tracePath = path.join(entryDir, "trace.jsonl");
      if (fs.existsSync(tracePath)) {
        traceFile = path.relative(resultDir, tracePath);
      }

      let entryAnalysis: string | null = null;
      const analysisPath = path.join(entryDir, "analysis.md");
      if (fs.existsSync(analysisPath)) {
        entryAnalysis = fs.readFileSync(analysisPath, "utf-8");
      }

      entries.push({
        evalInput,
        evalOutput,
        evaluations,
        expectation: (entryConfig["expectation"] as JsonValue) ?? null,
        evaluators: (entryConfig["evaluators"] as string[]) ?? [],
        evalMetadata:
          (entryConfig["evalMetadata"] as Record<string, JsonValue>) ?? null,
        description: (entryConfig["description"] as string) ?? null,
        traceFile,
        analysis: entryAnalysis,
      });
      entryIdx++;
    }

    datasets.push({
      dataset: dsMeta["dataset"] as string,
      datasetPath: dsMeta["datasetPath"] as string,
      runnable: dsMeta["runnable"] as string,
      entries,
    });
    dsIdx++;
  }

  return {
    testId: meta["testId"] as string,
    command: meta["command"] as string,
    startedAt: meta["startedAt"] as string,
    endedAt: meta["endedAt"] as string,
    datasets,
  };
}
