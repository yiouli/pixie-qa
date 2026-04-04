"use strict";
/**
 * Test result models and persistence for `pixie test`.
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.generateTestId = generateTestId;
exports.saveTestResult = saveTestResult;
exports.loadTestResult = loadTestResult;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
// ── Functions ────────────────────────────────────────────────────────────────
/** Generate a timestamped test run ID (YYYYMMDD-HHMMSS). */
function generateTestId() {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    return (`${now.getUTCFullYear()}${pad(now.getUTCMonth() + 1)}${pad(now.getUTCDate())}-` +
        `${pad(now.getUTCHours())}${pad(now.getUTCMinutes())}${pad(now.getUTCSeconds())}`);
}
function resultToDict(result) {
    const datasets = [];
    for (const ds of result.datasets) {
        const entryDicts = [];
        for (const entry of ds.entries) {
            const evalDicts = entry.evaluations.map((ev) => ({
                evaluator: ev.evaluator,
                score: ev.score,
                reasoning: ev.reasoning,
            }));
            const entryDict = {
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
function metadataToDict(result) {
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
function saveTestResult(result) {
    const { getConfig } = require("../config");
    const config = getConfig();
    const resultDir = path_1.default.join(config.root, "results", result.testId);
    fs_1.default.mkdirSync(resultDir, { recursive: true });
    const filepath = path_1.default.join(resultDir, "result.json");
    const payload = {
        meta: metadataToDict(result),
        datasets: resultToDict(result),
    };
    fs_1.default.writeFileSync(filepath, JSON.stringify(payload, null, 2), "utf-8");
    return path_1.default.resolve(filepath);
}
/**
 * Load a test result from `<pixie_root>/results/<testId>/result.json`.
 *
 * Also reads any `dataset-<index>.md` analysis files.
 */
function loadTestResult(testId) {
    const { getConfig } = require("../config");
    const config = getConfig();
    const resultDir = path_1.default.join(config.root, "results", testId);
    const filepath = path_1.default.join(resultDir, "result.json");
    const data = JSON.parse(fs_1.default.readFileSync(filepath, "utf-8"));
    const meta = data.meta;
    const datasets = [];
    for (let i = 0; i < data.datasets.length; i++) {
        const dsData = data.datasets[i];
        const entries = [];
        for (const entryData of dsData.entries) {
            const evaluations = entryData.evaluations.map((ev) => ({
                evaluator: ev.evaluator,
                score: ev.score,
                reasoning: ev.reasoning,
            }));
            entries.push({
                input: entryData.input,
                output: entryData.output,
                expectedOutput: entryData.expectedOutput ?? null,
                description: entryData.description ?? null,
                evaluations,
            });
        }
        // Load analysis markdown if it exists
        const analysisPath = path_1.default.join(resultDir, `dataset-${i}.md`);
        let analysis = null;
        if (fs_1.default.existsSync(analysisPath)) {
            analysis = fs_1.default.readFileSync(analysisPath, "utf-8");
        }
        datasets.push({
            dataset: dsData.dataset,
            entries,
            analysis,
        });
    }
    return {
        testId: meta.testId,
        command: meta.command,
        startedAt: meta.startedAt,
        endedAt: meta.endedAt,
        datasets,
    };
}
//# sourceMappingURL=testResult.js.map