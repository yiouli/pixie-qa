"use strict";
/**
 * Scorecard data models and HTML report generation.
 *
 * Provides DatasetEntryResult, DatasetScorecard types and
 * generateDatasetScorecardHtml(), saveDatasetScorecard() functions.
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.evaluatorDisplayName = evaluatorDisplayName;
exports.createDatasetScorecard = createDatasetScorecard;
exports.generateDatasetScorecardHtml = generateDatasetScorecardHtml;
exports.saveDatasetScorecard = saveDatasetScorecard;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
// ── Constants ────────────────────────────────────────────────────────────────
const PIXIE_REPO_URL = "https://github.com/yiouli/pixie-qa";
const PIXIE_FEEDBACK_URL = "https://feedback.gopixie.ai/feedback";
const PIXIE_BRAND_ICON_URL = "https://github.com/user-attachments/assets/76c18199-f00a-4fb3-a12f-ce6c173727af";
const DATA_PLACEHOLDER = '"__PIXIE_DATA_PLACEHOLDER__"';
// ── Helpers ──────────────────────────────────────────────────────────────────
/** Derive a human-readable name from an evaluator callable. */
function evaluatorDisplayName(evaluator) {
    if (evaluator && typeof evaluator === "object") {
        const nameAttr = evaluator["name"];
        if (typeof nameAttr === "string")
            return nameAttr;
    }
    if (typeof evaluator === "function") {
        if (evaluator.name)
            return evaluator.name;
    }
    if (evaluator && typeof evaluator === "object") {
        const ctorName = evaluator.constructor?.name;
        if (ctorName && ctorName !== "Object" && ctorName !== "function") {
            return ctorName;
        }
    }
    return String(evaluator);
}
/** Load the compiled React scorecard HTML template. */
function loadTemplate() {
    const templatePath = path_1.default.resolve(__dirname, "..", "assets", "index.html");
    if (!fs_1.default.existsSync(templatePath)) {
        throw new Error(`Scorecard template not found at ${templatePath}. ` +
            "Run the frontend build first.");
    }
    return fs_1.default.readFileSync(templatePath, "utf-8");
}
/** Convert an arbitrary string into a safe filename fragment. */
function normaliseFilename(s) {
    let result = "";
    for (const c of s) {
        if (/[a-zA-Z0-9_-]/.test(c)) {
            result += c;
        }
        else {
            result += "-";
        }
    }
    result = result.replace(/-+/g, "-").replace(/^-+|-+$/g, "");
    return result.slice(0, 60);
}
/** Create a DatasetScorecard with default timestamp. */
function createDatasetScorecard(opts) {
    return {
        datasetName: opts.datasetName,
        entries: opts.entries,
        timestamp: opts.timestamp ?? new Date(),
    };
}
// ── Serialization ────────────────────────────────────────────────────────────
function datasetScorecardToDict(scorecard, commandArgs) {
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
    const assertDicts = [];
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
    const status = allPass ? "passed" : "failed";
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
function generateDatasetScorecardHtml(scorecard, commandArgs) {
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
function saveDatasetScorecard(scorecard, commandArgs) {
    const { getConfig } = require("../config");
    const config = getConfig();
    const scorecardDir = path_1.default.join(config.root, "scorecards");
    fs_1.default.mkdirSync(scorecardDir, { recursive: true });
    const pad = (n) => String(n).padStart(2, "0");
    const d = scorecard.timestamp;
    const tsStr = `${d.getUTCFullYear()}${pad(d.getUTCMonth() + 1)}${pad(d.getUTCDate())}-${pad(d.getUTCHours())}${pad(d.getUTCMinutes())}${pad(d.getUTCSeconds())}`;
    const safeName = normaliseFilename(scorecard.datasetName);
    const filename = safeName ? `${tsStr}-${safeName}.html` : `${tsStr}.html`;
    const filepath = path_1.default.join(scorecardDir, filename);
    const htmlContent = generateDatasetScorecardHtml(scorecard, commandArgs);
    fs_1.default.writeFileSync(filepath, htmlContent, "utf-8");
    return path_1.default.resolve(filepath);
}
//# sourceMappingURL=scorecard.js.map