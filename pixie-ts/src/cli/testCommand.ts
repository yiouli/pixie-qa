/**
 * pixie test — dataset-driven eval orchestrator.
 */

import path from "node:path";
import { getConfig } from "../config.js";
import { configureRateLimitsFromConfig } from "../eval/rateLimiter.js";
import { discoverDatasetFiles, runDataset } from "../harness/runner.js";
import {
  generateTestId,
  saveTestResult,
  type RunResult,
  type DatasetResult,
  isEvaluationResult,
} from "../harness/runResult.js";

/**
 * Run dataset evaluations and return exit code.
 */
export async function runTest(opts: {
  testPath?: string | null;
  verbose?: boolean;
  noOpen?: boolean;
}): Promise<number> {
  const config = getConfig();
  configureRateLimitsFromConfig(config);

  const testPath = opts.testPath ?? config.datasetDir;
  const datasets = discoverDatasetFiles(testPath);

  if (datasets.length === 0) {
    console.error(`No dataset files found at: ${testPath}`);
    return 1;
  }

  const testId = generateTestId();
  const startedAt = new Date().toISOString();
  const datasetResults: DatasetResult[] = [];

  for (const dsPath of datasets) {
    try {
      const [name, runnable, entries] = await runDataset(dsPath);

      const dsResult: DatasetResult = {
        dataset: name,
        datasetPath: dsPath,
        runnable,
        entries,
      };
      datasetResults.push(dsResult);

      // Print console output
      console.log(`\n${name}`);
      console.log("─".repeat(60));
      for (let i = 0; i < entries.length; i++) {
        const entry = entries[i];
        const evaluatorNames = entry.evaluations.map((e) => e.evaluator);
        const scores = entry.evaluations
          .map((e) => {
            if (isEvaluationResult(e)) {
              return e.score >= 0.7
                ? `✓ ${e.score.toFixed(2)}`
                : `✗ ${e.score.toFixed(2)}`;
            }
            return "⏳ pending";
          })
          .join(", ");

        const desc = entry.description ?? `Entry ${i + 1}`;
        console.log(`  ${desc}  (${evaluatorNames.join(", ")})  [${scores}]`);

        if (opts.verbose) {
          for (const ev of entry.evaluations) {
            if (isEvaluationResult(ev)) {
              console.log(
                `    ${ev.evaluator}: ${ev.score.toFixed(2)} — ${ev.reasoning}`,
              );
            }
          }
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error(`Error processing ${dsPath}: ${msg}`);
    }
  }

  const endedAt = new Date().toISOString();
  const result: RunResult = {
    testId,
    command: `pixie-qa test ${opts.testPath ?? ""}`.trim(),
    startedAt,
    endedAt,
    datasets: datasetResults,
  };

  const resultDir = saveTestResult(result);
  console.log(`\nResults saved to: ${resultDir}`);

  return 0;
}
