/**
 * Scorecard data models and HTML report generation.
 *
 * Provides DatasetEntryResult, DatasetScorecard types and
 * generateDatasetScorecardHtml(), saveDatasetScorecard() functions.
 */

import fs from "fs";
import path from "path";

import type { Evaluation } from "./evaluation";

// ── Constants ────────────────────────────────────────────────────────────────

const PIXIE_REPO_URL = "https://github.com/yiouli/pixie-qa";
const PIXIE_FEEDBACK_URL = "https://feedback.gopixie.ai/feedback";
const PIXIE_BRAND_ICON_URL =
  "https://github.com/user-attachments/assets/76c18199-f00a-4fb3-a12f-ce6c173727af";

const DATA_PLACEHOLDER = '"__PIXIE_DATA_PLACEHOLDER__"';

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Derive a human-readable name from an evaluator callable. */
export function evaluatorDisplayName(evaluator: unknown): string {
  if (evaluator && typeof evaluator === "object") {
    const nameAttr = (evaluator as Record<string, unknown>)["name"];
    if (typeof nameAttr === "string") return nameAttr;
  }
  if (typeof evaluator === "function") {
    if (evaluator.name) return evaluator.name;
  }
  if (evaluator && typeof evaluator === "object") {
    const ctorName = (evaluator as object).constructor?.name;
    if (ctorName && ctorName !== "Object" && ctorName !== "function") {
      return ctorName;
    }
  }
  return String(evaluator);
}

/** Load the compiled React scorecard HTML template. */
function loadTemplate(): string {
  const templatePath = path.resolve(
    __dirname,
    "..",
    "assets",
    "index.html"
  );
  if (!fs.existsSync(templatePath)) {
    throw new Error(
      `Scorecard template not found at ${templatePath}. ` +
        "Run the frontend build first."
    );
  }
  return fs.readFileSync(templatePath, "utf-8");
}

/** Convert an arbitrary string into a safe filename fragment. */
function normaliseFilename(s: string): string {
  let result = "";
  for (const c of s) {
    if (/[a-zA-Z0-9_-]/.test(c)) {
      result += c;
    } else {
      result += "-";
    }
  }
  result = result.replace(/-+/g, "-").replace(/^-+|-+$/g, "");
  return result.slice(0, 60);
}

// ── Types ────────────────────────────────────────────────────────────────────

/** Evaluation results for a single dataset entry. */
export interface DatasetEntryResult {
  readonly evaluatorNames: readonly string[];
  readonly evaluations: readonly Evaluation[];
  readonly inputLabel: string;
  readonly evaluableDict: Record<string, unknown>;
}

/** Scorecard for a single dataset evaluation run. */
export interface DatasetScorecard {
  readonly datasetName: string;
  readonly entries: DatasetEntryResult[];
  readonly timestamp: Date;
}

/** Create a DatasetScorecard with default timestamp. */
export function createDatasetScorecard(opts: {
  datasetName: string;
  entries: DatasetEntryResult[];
  timestamp?: Date;
}): DatasetScorecard {
  return {
    datasetName: opts.datasetName,
    entries: opts.entries,
    timestamp: opts.timestamp ?? new Date(),
  };
}

// ── Serialization ────────────────────────────────────────────────────────────

function datasetScorecardToDict(
  scorecard: DatasetScorecard,
  commandArgs: string
): Record<string, unknown> {
  const ts = scorecard.timestamp
    .toISOString()
    .replace("T", " ")
    .replace(/\.\d{3}Z$/, " UTC");

  // Count passed entries (all evaluators score >= 0.5)
  let passedEntries = 0;
  for (const entry of scorecard.entries) {
    if (entry.evaluations.every((e) => e.score >= 0.5)) {
      passedEntries++;
    }
  }
  const totalEntries = scorecard.entries.length;

  // Map each entry to an AssertRecord-shaped dict
  const assertDicts: Array<Record<string, unknown>> = [];
  for (const entry of scorecard.entries) {
    assertDicts.push({
      evaluator_names: [...entry.evaluatorNames],
      input_labels: [entry.inputLabel],
      results: [
        entry.evaluations.map((ev) => ({
          score: ev.score,
          reasoning: ev.reasoning,
          details: ev.details,
        })),
      ],
      passed: entry.evaluations.every((e) => e.score >= 0.5),
      criteria_message: "",
      scoring_strategy: "",
      evaluable_dicts: [entry.evaluableDict],
    });
  }

  const allPass = passedEntries === totalEntries;
  const status: "passed" | "failed" = allPass ? "passed" : "failed";

  return {
    command_args: commandArgs,
    timestamp: ts,
    summary: `${passedEntries}/${totalEntries} entries passed`,
    pixie_repo_url: PIXIE_REPO_URL,
    feedback_url: PIXIE_FEEDBACK_URL,
    brand_icon_url: PIXIE_BRAND_ICON_URL,
    test_records: [
      {
        name: scorecard.datasetName,
        status,
        message: null,
        asserts: assertDicts,
      },
    ],
  };
}

// ── Public API ───────────────────────────────────────────────────────────────

/** Render a DatasetScorecard as a self-contained HTML page. */
export function generateDatasetScorecardHtml(
  scorecard: DatasetScorecard,
  commandArgs: string
): string {
  const template = loadTemplate();
  const data = datasetScorecardToDict(scorecard, commandArgs);
  const dataJson = JSON.stringify(data);
  return template.replace(DATA_PLACEHOLDER, dataJson);
}

/**
 * Generate and save a dataset scorecard HTML to disk.
 *
 * Saves to `{config.root}/scorecards/<timestamp>-<name>.html`.
 *
 * @returns The absolute path of the saved HTML file.
 */
export function saveDatasetScorecard(
  scorecard: DatasetScorecard,
  commandArgs: string
): string {
  const { getConfig } = require("../config");
  const config = getConfig();
  const scorecardDir = path.join(config.root, "scorecards");
  fs.mkdirSync(scorecardDir, { recursive: true });

  const pad = (n: number) => String(n).padStart(2, "0");
  const d = scorecard.timestamp;
  const tsStr = `${d.getUTCFullYear()}${pad(d.getUTCMonth() + 1)}${pad(d.getUTCDate())}-${pad(d.getUTCHours())}${pad(d.getUTCMinutes())}${pad(d.getUTCSeconds())}`;
  const safeName = normaliseFilename(scorecard.datasetName);
  const filename = safeName ? `${tsStr}-${safeName}.html` : `${tsStr}.html`;
  const filepath = path.join(scorecardDir, filename);

  const htmlContent = generateDatasetScorecardHtml(scorecard, commandArgs);
  fs.writeFileSync(filepath, htmlContent, "utf-8");

  return path.resolve(filepath);
}
