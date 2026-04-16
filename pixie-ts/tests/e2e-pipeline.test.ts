/**
 * Full-pipeline e2e test: load dataset → resolve evaluators → run → evaluate → save.
 *
 * Uses the e2e_fixtures/datasets/customer-faq.json dataset with deterministic
 * mock evaluators — no API keys or network calls required.
 */
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import {
  loadDataset,
  runDataset,
} from "../src/harness/runner.js";
import {
  saveTestResult,
  generateTestId,
  isEvaluationResult,
  type RunResult,
  type DatasetResult,
} from "../src/harness/runResult.js";
import { configureRateLimits } from "../src/eval/rateLimiter.js";

const FIXTURE_DATASET = path.resolve(
  __dirname,
  "e2e_fixtures/datasets/customer-faq.json",
);

describe("e2e: full pipeline with customer-faq fixture", () => {
  let tmpDir: string;
  const originalEnv = { ...process.env };

  beforeAll(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "pixie-ts-e2e-pipeline-"));
    process.env["PIXIE_ROOT"] = tmpDir;
    // Disable rate limiting for tests
    configureRateLimits(null);
  });

  afterAll(() => {
    for (const key of Object.keys(process.env)) {
      if (key.startsWith("PIXIE_")) delete process.env[key];
    }
    Object.assign(process.env, originalEnv);
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it("loads the customer-faq dataset", () => {
    const dataset = loadDataset(FIXTURE_DATASET);
    expect(dataset.name).toBe("customer-faq");
    expect(dataset.entries).toHaveLength(5);
    expect(dataset.entries[0].description).toBe(
      "Baggage allowance — exact match expected",
    );
    // First entry has default evaluator + MockClosedQAEval
    expect(dataset.entries[0].evaluators).toHaveLength(2);
  });

  it("runs the full dataset and produces results for all 5 entries", async () => {
    const [name, runnable, entries] = await runDataset(FIXTURE_DATASET);

    expect(name).toBe("customer-faq");
    expect(entries).toHaveLength(5);

    // Every entry should have evaluations
    for (let i = 0; i < entries.length; i++) {
      const entry = entries[i];
      expect(entry.evaluations.length).toBeGreaterThan(0);
      expect(entry.evalOutput.length).toBeGreaterThan(0);

      // All evaluations should be completed (not pending)
      for (const ev of entry.evaluations) {
        expect(isEvaluationResult(ev)).toBe(true);
        if (isEvaluationResult(ev)) {
          expect(ev.score).toBeGreaterThanOrEqual(0.0);
          expect(ev.score).toBeLessThanOrEqual(1.0);
          expect(ev.reasoning).toBeTruthy();
        }
      }
    }
  });

  it("entry 1 (baggage) scores high on factuality", async () => {
    const [, , entries] = await runDataset(FIXTURE_DATASET);
    const baggage = entries[0];

    // MockFactualityEval should score high — output exactly matches expected
    const factuality = baggage.evaluations.find(
      (e) => isEvaluationResult(e) && e.evaluator === "MockFactualityEval",
    );
    expect(factuality).toBeDefined();
    if (factuality && isEvaluationResult(factuality)) {
      expect(factuality.score).toBeGreaterThanOrEqual(0.8);
    }
  });

  it("entry 5 (meals) has a low MockStrictTone score", async () => {
    const [, , entries] = await runDataset(FIXTURE_DATASET);
    const meals = entries[4];

    const tone = meals.evaluations.find(
      (e) => isEvaluationResult(e) && e.evaluator === "MockStrictTone",
    );
    expect(tone).toBeDefined();
    if (tone && isEvaluationResult(tone)) {
      expect(tone.score).toBe(0.2);
    }
  });

  it("saves results to disk and verifies structure", async () => {
    const [name, runnable, entries] = await runDataset(FIXTURE_DATASET);
    const testId = generateTestId();
    const result: RunResult = {
      testId,
      command: "pixie-qa test e2e",
      startedAt: new Date().toISOString(),
      endedAt: new Date().toISOString(),
      datasets: [
        {
          dataset: name,
          datasetPath: FIXTURE_DATASET,
          runnable,
          entries,
        },
      ],
    };

    const resultDir = saveTestResult(result);
    expect(fs.existsSync(resultDir)).toBe(true);

    // meta.json
    const meta = JSON.parse(
      fs.readFileSync(path.join(resultDir, "meta.json"), "utf-8"),
    ) as Record<string, unknown>;
    expect(meta["testId"]).toBe(testId);

    // dataset-0/
    const dsDir = path.join(resultDir, "dataset-0");
    expect(fs.existsSync(dsDir)).toBe(true);

    // 5 entry directories
    for (let i = 0; i < 5; i++) {
      const entryDir = path.join(dsDir, `entry-${i}`);
      expect(fs.existsSync(entryDir)).toBe(true);
      expect(fs.existsSync(path.join(entryDir, "evaluations.jsonl"))).toBe(true);
      expect(fs.existsSync(path.join(entryDir, "eval-input.jsonl"))).toBe(true);
      expect(fs.existsSync(path.join(entryDir, "eval-output.jsonl"))).toBe(true);
      expect(fs.existsSync(path.join(entryDir, "config.json"))).toBe(true);
    }
  });
});
