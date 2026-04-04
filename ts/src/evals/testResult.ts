/**
 * Test result models and persistence for `pixie test`.
 */

import fs from "fs";
import path from "path";

import type { JsonValue } from "../storage/evaluable";

// ── Interfaces ───────────────────────────────────────────────────────────────

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

// ── Functions ────────────────────────────────────────────────────────────────

/** Generate a timestamped test run ID (YYYYMMDD-HHMMSS). */
export function generateTestId(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${now.getUTCFullYear()}${pad(now.getUTCMonth() + 1)}${pad(now.getUTCDate())}-` +
    `${pad(now.getUTCHours())}${pad(now.getUTCMinutes())}${pad(now.getUTCSeconds())}`
  );
}

function resultToDict(
  result: RunResult
): Array<Record<string, unknown>> {
  const datasets: Array<Record<string, unknown>> = [];
  for (const ds of result.datasets) {
    const entryDicts: Array<Record<string, unknown>> = [];
    for (const entry of ds.entries) {
      const evalDicts = entry.evaluations.map((ev) => ({
        evaluator: ev.evaluator,
        score: ev.score,
        reasoning: ev.reasoning,
      }));
      const entryDict: Record<string, unknown> = {
        input: entry.input,
        output: entry.output,
        evaluations: evalDicts,
      };
      if (entry.expectedOutput !== null) {
        entryDict["expectedOutput"] = entry.expectedOutput;
      }
      if (entry.description !== null) {
        entryDict["description"] = entry.description;
      }
      entryDicts.push(entryDict);
    }
    datasets.push({
      dataset: ds.dataset,
      entries: entryDicts,
    });
  }
  return datasets;
}

function metadataToDict(
  result: RunResult
): Record<string, unknown> {
  return {
    testId: result.testId,
    command: result.command,
    startedAt: result.startedAt,
    endedAt: result.endedAt,
  };
}

/**
 * Write test result JSON to `<pixie_root>/results/<testId>/result.json`.
 *
 * @returns The absolute path of the saved JSON file.
 */
export function saveTestResult(result: RunResult): string {
  const { getConfig } = require("../config");
  const config = getConfig();
  const resultDir = path.join(config.root, "results", result.testId);
  fs.mkdirSync(resultDir, { recursive: true });

  const filepath = path.join(resultDir, "result.json");
  const payload = {
    meta: metadataToDict(result),
    datasets: resultToDict(result),
  };
  fs.writeFileSync(filepath, JSON.stringify(payload, null, 2), "utf-8");

  return path.resolve(filepath);
}

/**
 * Load a test result from `<pixie_root>/results/<testId>/result.json`.
 *
 * Also reads any `dataset-<index>.md` analysis files.
 */
export function loadTestResult(testId: string): RunResult {
  const { getConfig } = require("../config");
  const config = getConfig();
  const resultDir = path.join(config.root, "results", testId);
  const filepath = path.join(resultDir, "result.json");

  const data = JSON.parse(fs.readFileSync(filepath, "utf-8"));
  const meta = data.meta;

  const datasets: DatasetResult[] = [];
  for (let i = 0; i < data.datasets.length; i++) {
    const dsData = data.datasets[i];
    const entries: EntryResult[] = [];
    for (const entryData of dsData.entries) {
      const evaluations: EvaluationResult[] = entryData.evaluations.map(
        (ev: Record<string, unknown>) => ({
          evaluator: ev.evaluator as string,
          score: ev.score as number,
          reasoning: ev.reasoning as string,
        })
      );
      entries.push({
        input: entryData.input as JsonValue,
        output: entryData.output as JsonValue,
        expectedOutput: (entryData.expectedOutput as JsonValue) ?? null,
        description: (entryData.description as string) ?? null,
        evaluations,
      });
    }

    // Load analysis markdown if it exists
    const analysisPath = path.join(resultDir, `dataset-${i}.md`);
    let analysis: string | null = null;
    if (fs.existsSync(analysisPath)) {
      analysis = fs.readFileSync(analysisPath, "utf-8");
    }

    datasets.push({
      dataset: dsData.dataset as string,
      entries,
      analysis,
    });
  }

  return {
    testId: meta.testId as string,
    command: meta.command as string,
    startedAt: meta.startedAt as string,
    endedAt: meta.endedAt as string,
    datasets,
  };
}
