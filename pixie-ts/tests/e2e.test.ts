import { describe, it, expect, beforeAll, afterAll } from "vitest";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { discoverDatasetFiles, loadDataset } from "../src/harness/runner.js";
import {
  saveTestResult,
  loadTestResult,
  generateTestId,
  type RunResult,
} from "../src/harness/runResult.js";

describe("e2e: discoverDatasetFiles", () => {
  let tmpDir: string;

  beforeAll(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "pixie-e2e-discover-"));
    // Create nested dataset files
    fs.mkdirSync(path.join(tmpDir, "datasets"), { recursive: true });
    fs.writeFileSync(path.join(tmpDir, "datasets", "test1.json"), "{}");
    fs.writeFileSync(path.join(tmpDir, "datasets", "test2.json"), "{}");
    fs.writeFileSync(path.join(tmpDir, "datasets", "readme.txt"), "not json");
  });

  afterAll(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it("finds all .json files in a directory", () => {
    const files = discoverDatasetFiles(path.join(tmpDir, "datasets"));
    expect(files).toHaveLength(2);
    expect(files.every((f) => f.endsWith(".json"))).toBe(true);
  });

  it("returns single file when given a .json file path", () => {
    const files = discoverDatasetFiles(
      path.join(tmpDir, "datasets", "test1.json"),
    );
    expect(files).toHaveLength(1);
  });

  it("returns empty array for non-existent path", () => {
    const files = discoverDatasetFiles("/nonexistent/path");
    expect(files).toEqual([]);
  });
});

describe("e2e: loadDataset", () => {
  let tmpDir: string;

  beforeAll(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "pixie-e2e-load-"));
  });

  afterAll(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it("loads a valid dataset file", () => {
    const datasetPath = path.join(tmpDir, "valid.json");
    const dataset = {
      name: "test-dataset",
      runnable: "./my_app.js:run",
      evaluators: ["ExactMatch"],
      entries: [
        {
          input_data: { question: "What is 2+2?" },
          description: "Simple math",
          expectation: "4",
        },
      ],
    };
    fs.writeFileSync(datasetPath, JSON.stringify(dataset), "utf-8");

    const loaded = loadDataset(datasetPath);
    expect(loaded.name).toBe("test-dataset");
    expect(loaded.runnable).toBe("./my_app.js:run");
    expect(loaded.entries).toHaveLength(1);
    expect(loaded.entries[0].description).toBe("Simple math");
    expect(loaded.entries[0].evaluators).toEqual(["ExactMatch"]);
  });

  it("throws for missing runnable field", () => {
    const datasetPath = path.join(tmpDir, "no-runnable.json");
    fs.writeFileSync(
      datasetPath,
      JSON.stringify({
        entries: [{ input_data: { q: "hi" }, description: "test" }],
      }),
      "utf-8",
    );
    expect(() => loadDataset(datasetPath)).toThrow("runnable");
  });

  it("throws for empty entries array", () => {
    const datasetPath = path.join(tmpDir, "empty-entries.json");
    fs.writeFileSync(
      datasetPath,
      JSON.stringify({ runnable: "./app.js:run", entries: [] }),
      "utf-8",
    );
    expect(() => loadDataset(datasetPath)).toThrow("non-empty array");
  });

  it("throws for missing description", () => {
    const datasetPath = path.join(tmpDir, "no-desc.json");
    fs.writeFileSync(
      datasetPath,
      JSON.stringify({
        runnable: "./app.js:run",
        evaluators: ["ExactMatch"],
        entries: [{ input_data: { q: "hi" } }],
      }),
      "utf-8",
    );
    expect(() => loadDataset(datasetPath)).toThrow("description");
  });

  it("supports per-row evaluator expansion with ...", () => {
    const datasetPath = path.join(tmpDir, "expand.json");
    fs.writeFileSync(
      datasetPath,
      JSON.stringify({
        runnable: "./app.js:run",
        evaluators: ["ExactMatch"],
        entries: [
          {
            input_data: { q: "test" },
            description: "Row with expansion",
            evaluators: ["...", "LevenshteinMatch"],
          },
        ],
      }),
      "utf-8",
    );

    const loaded = loadDataset(datasetPath);
    // "..." expands to default evaluators + LevenshteinMatch
    expect(loaded.entries[0].evaluators).toEqual([
      "ExactMatch",
      "LevenshteinMatch",
    ]);
  });
});

describe("e2e: saveTestResult + loadTestResult", () => {
  let tmpDir: string;
  const originalEnv = { ...process.env };

  beforeAll(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "pixie-e2e-save-"));
    process.env["PIXIE_ROOT"] = tmpDir;
  });

  afterAll(() => {
    process.env = { ...originalEnv };
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it("saves and loads test results round-trip", () => {
    const testId = generateTestId();
    const result: RunResult = {
      testId,
      command: "pixie-qa test",
      startedAt: "2024-01-01T00:00:00Z",
      endedAt: "2024-01-01T00:01:00Z",
      datasets: [
        {
          dataset: "test-ds",
          datasetPath: "/tmp/test.json",
          runnable: "./app.js:run",
          entries: [
            {
              evalInput: [{ name: "question", value: "hello" }],
              evalOutput: [{ name: "answer", value: "world" }],
              evaluations: [
                { evaluator: "ExactMatch", score: 1.0, reasoning: "match" },
              ],
              expectation: "world",
              evaluators: ["ExactMatch"],
              evalMetadata: null,
              description: "Test entry",
            },
          ],
        },
      ],
    };

    const resultDir = saveTestResult(result);
    expect(fs.existsSync(resultDir)).toBe(true);

    // Verify meta.json was written
    const metaPath = path.join(resultDir, "meta.json");
    expect(fs.existsSync(metaPath)).toBe(true);
    const meta = JSON.parse(fs.readFileSync(metaPath, "utf-8")) as Record<
      string,
      unknown
    >;
    expect(meta["testId"]).toBe(testId);

    // Verify dataset directory was created
    const dsDir = path.join(resultDir, "dataset-0");
    expect(fs.existsSync(dsDir)).toBe(true);

    // Verify entry directory was created
    const entryDir = path.join(dsDir, "entry-0");
    expect(fs.existsSync(entryDir)).toBe(true);

    // Verify evaluations.jsonl was written
    const evalsPath = path.join(entryDir, "evaluations.jsonl");
    expect(fs.existsSync(evalsPath)).toBe(true);
    const evalsContent = fs.readFileSync(evalsPath, "utf-8").trim();
    const evalLine = JSON.parse(evalsContent) as Record<string, unknown>;
    expect(evalLine["evaluator"]).toBe("ExactMatch");
    expect(evalLine["score"]).toBe(1.0);
  });
});
