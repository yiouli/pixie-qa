/**
 * `pixie-qa analyze` CLI command.
 *
 * Generates analysis and recommendations for a test run result by
 * running an LLM agent (via OpenAI API) on each dataset's results.
 *
 * Usage:
 *   pixie-qa analyze <test_run_id>
 *
 * The analysis markdown is saved alongside the result JSON at
 * `<pixie_root>/results/<test_id>/dataset-<index>.md`.
 */

import fs from "fs";
import path from "path";

import type { DatasetResult } from "../evals/testResult";
import { loadTestResult } from "../evals/testResult";
import { getConfig } from "../config";

function buildAnalysisPrompt(ds: DatasetResult): string {
  const lines: string[] = [];
  lines.push(`Dataset: ${ds.dataset}`);
  lines.push("");

  const passed = ds.entries.filter((e) =>
    e.evaluations.every((ev) => ev.score >= 0.5)
  ).length;
  lines.push(`Overall: ${passed}/${ds.entries.length} entries passed`);
  lines.push("");

  for (let i = 0; i < ds.entries.length; i++) {
    const entry = ds.entries[i];
    const desc = entry.description ?? JSON.stringify(entry.input);
    const allPass = entry.evaluations.every((ev) => ev.score >= 0.5);
    const status = allPass ? "PASS" : "FAIL";
    lines.push(`Entry ${i + 1} (${status}): ${desc}`);
    lines.push(`  Input: ${JSON.stringify(entry.input)}`);
    lines.push(`  Output: ${JSON.stringify(entry.output)}`);
    if (entry.expectedOutput !== null) {
      lines.push(`  Expected: ${JSON.stringify(entry.expectedOutput)}`);
    }
    for (const ev of entry.evaluations) {
      const passMark = ev.score >= 0.5 ? "PASS" : "FAIL";
      lines.push(
        `  - ${ev.evaluator}: ${ev.score.toFixed(2)} (${passMark}) — ${ev.reasoning}`
      );
    }
    lines.push("");
  }

  return lines.join("\n");
}

const SYSTEM_PROMPT = `You are a QA analysis expert. Given evaluation results from an AI application \
test run, provide:

1. **Summary** — A brief overview of the test results highlighting key patterns.
2. **Failure Analysis** — For each failing scenario, explain what went wrong and \
why the evaluator scored it low.
3. **Recommendations** — Actionable steps to improve the AI application's quality \
based on the failures observed.

Output your analysis as well-structured Markdown. Be concise and actionable. \
Focus on patterns across failures rather than repeating individual scores.`;

async function analyzeDataset(
  ds: DatasetResult,
  index: number,
  resultDir: string
): Promise<string> {
  const { default: OpenAI } = await import("openai");

  const promptText = buildAnalysisPrompt(ds);

  const client = new OpenAI();
  const response = await client.chat.completions.create({
    model: process.env["PIXIE_ANALYZE_MODEL"] ?? "gpt-4o-mini",
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      { role: "user", content: promptText },
    ],
    temperature: 0.3,
  });

  const content = response.choices[0].message.content ?? "";

  // Save to disk
  const analysisPath = path.join(resultDir, `dataset-${index}.md`);
  fs.writeFileSync(analysisPath, content, "utf-8");

  return content;
}

async function analyzeAll(testId: string): Promise<void> {
  const result = loadTestResult(testId);
  const config = getConfig();
  const resultDir = path.join(config.root, "results", testId);

  const tasks = result.datasets.map((ds, i) =>
    analyzeDataset(ds, i, resultDir)
  );
  await Promise.all(tasks);
}

/**
 * Entry point for `pixie-qa analyze <test_run_id>`.
 */
export async function analyze(testId: string): Promise<number> {
  try {
    loadTestResult(testId);
  } catch {
    console.error(`Error: No test result found for ID '${testId}'`);
    return 1;
  }

  const result = loadTestResult(testId);
  console.log(
    `Analyzing ${result.datasets.length} dataset(s) for test run ${testId}...`
  );

  await analyzeAll(testId);

  const config = getConfig();
  const resultDir = path.join(config.root, "results", testId);
  console.log(`Analysis saved to ${resultDir}`);
  return 0;
}
