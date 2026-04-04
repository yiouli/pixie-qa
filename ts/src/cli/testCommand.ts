/**
 * `pixie-qa test` CLI entry point.
 *
 * Usage:
 *   pixie-qa test [path] [--verbose] [--no-open]
 *
 * Dataset mode — when `path` is a `.json` file or a directory
 * containing dataset JSON files. Each dataset produces its own result.
 * Default — no path searches the pixie datasets directory.
 */

import path from "path";

import type { Evaluable } from "../storage/evaluable";
import {
  discoverDatasetFiles,
  loadDatasetEntries,
} from "../evals/datasetRunner";
import type { Evaluation } from "../evals/evaluation";
import { evaluate } from "../evals/evaluation";
import type {
  DatasetResult,
  EntryResult,
  EvaluationResult,
  RunResult,
} from "../evals/testResult";
import {
  generateTestId,
  saveTestResult,
} from "../evals/testResult";
import { getConfig } from "../config";

/**
 * Run evaluations for a single dataset and return a DatasetResult.
 */
async function runDataset(datasetPath: string): Promise<DatasetResult> {
  const loaded = loadDatasetEntries(datasetPath);

  const entryResults: EntryResult[] = [];
  for (const [evaluable, evaluatorNames] of loaded.entries) {
    // Resolve evaluators dynamically
    const evaluators: Array<(e: Evaluable) => Evaluation | Promise<Evaluation>> = [];
    const shortNames: string[] = [];

    for (const name of evaluatorNames) {
      const lastDot = name.lastIndexOf(".");
      const sName = lastDot === -1 ? name : name.substring(lastDot + 1);
      shortNames.push(sName);

      try {
        const modulePath = name.substring(0, lastDot);
        const className = name.substring(lastDot + 1);
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const mod = require(modulePath);
        const cls = mod[className];
        if (typeof cls === "function") {
          evaluators.push(cls());
        } else {
          evaluators.push(cls);
        }
      } catch {
        // If evaluator can't be resolved, create a stub that returns 0
        evaluators.push(() => ({
          score: 0,
          reasoning: `Could not resolve evaluator: ${name}`,
          details: {},
        }));
      }
    }

    const evals: Evaluation[] = [];
    for (const ev of evaluators) {
      const result = await evaluate(ev, evaluable);
      evals.push(result);
    }

    const expOut = evaluable.expectedOutput;
    const expectedOutput =
      typeof expOut === "symbol" || expOut === null ? null : expOut;

    const evalResults: EvaluationResult[] = shortNames.map((name, i) => ({
      evaluator: name,
      score: evals[i].score,
      reasoning: evals[i].reasoning,
    }));

    entryResults.push({
      input: evaluable.evalInput,
      output: evaluable.evalOutput,
      expectedOutput,
      description: evaluable.description,
      evaluations: evalResults,
    });
  }

  return {
    dataset: loaded.name,
    entries: entryResults,
    analysis: null,
  };
}

/**
 * Main entry point for `pixie-qa test`.
 *
 * @returns Exit code: 0 if all tests pass, 1 otherwise.
 */
export async function testMain(opts: {
  path?: string;
  verbose?: boolean;
  noOpen?: boolean;
}): Promise<number> {
  const config = getConfig();
  const searchPath = opts.path ?? config.datasetDir;

  const datasetFiles = discoverDatasetFiles(searchPath);
  if (datasetFiles.length === 0) {
    console.log("No dataset files found.");
    return 1;
  }

  const commandStr = "pixie-qa test " + (opts.path ?? "");
  const testId = generateTestId();
  const startedAt = new Date().toISOString();
  let allPassed = true;
  const datasetResults: DatasetResult[] = [];

  for (const dsPath of datasetFiles) {
    let dsResult: DatasetResult;
    try {
      dsResult = await runDataset(path.resolve(dsPath));
    } catch (exc) {
      console.log(String(exc));
      return 1;
    }
    datasetResults.push(dsResult);

    // Print results
    const passedCount = dsResult.entries.filter((entry) =>
      entry.evaluations.every((ev) => ev.score >= 0.5)
    ).length;
    const totalCount = dsResult.entries.length;
    console.log(`\n${"=".repeat(52)} ${dsResult.dataset} ${"=".repeat(52)}`);
    for (let i = 0; i < dsResult.entries.length; i++) {
      const entry = dsResult.entries[i];
      const evalsStr = entry.evaluations.map((ev) => ev.evaluator).join(", ");
      const scores = entry.evaluations.map((ev) => ev.score.toFixed(2));
      const allPass = entry.evaluations.every((ev) => ev.score >= 0.5);
      const mark = allPass ? "\u2713" : "\u2717";
      let desc = entry.description ?? JSON.stringify(entry.input);
      if (desc.length > 80) desc = desc.substring(0, 80) + "\u2026";
      console.log(
        `  [${i + 1}] ${desc} (${evalsStr}) [${scores.join(", ")}] ${mark}`
      );
      if (!allPass) {
        allPassed = false;
        if (opts.verbose) {
          for (const ev of entry.evaluations) {
            if (ev.score < 0.5) {
              console.log(`      ${ev.evaluator}: ${ev.reasoning}`);
            }
          }
        }
      }
    }
    console.log(`  ${passedCount}/${totalCount} passed`);
  }

  const endedAt = new Date().toISOString();
  const runResult: RunResult = {
    testId,
    command: commandStr,
    startedAt,
    endedAt,
    datasets: datasetResults,
  };
  const resultPath = saveTestResult(runResult);
  console.log(`\nResults saved to ${resultPath}`);

  if (!opts.noOpen) {
    try {
      const { openWebui } = await import("../web/server");
      await openWebui(config.root, {
        tab: "results",
        itemId: `results/${testId}`,
      });
    } catch {
      // Web UI opening is best-effort
    }
  }

  return allPassed ? 0 : 1;
}
