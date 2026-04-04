"use strict";
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
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.analyze = analyze;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const testResult_1 = require("../evals/testResult");
const config_1 = require("../config");
function buildAnalysisPrompt(ds) {
    const lines = [];
    lines.push(`Dataset: ${ds.dataset}`);
    lines.push("");
    const passed = ds.entries.filter((e) => e.evaluations.every((ev) => ev.score >= 0.5)).length;
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
            lines.push(`  - ${ev.evaluator}: ${ev.score.toFixed(2)} (${passMark}) — ${ev.reasoning}`);
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
async function analyzeDataset(ds, index, resultDir) {
    const { default: OpenAI } = await Promise.resolve().then(() => __importStar(require("openai")));
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
    const analysisPath = path_1.default.join(resultDir, `dataset-${index}.md`);
    fs_1.default.writeFileSync(analysisPath, content, "utf-8");
    return content;
}
async function analyzeAll(testId) {
    const result = (0, testResult_1.loadTestResult)(testId);
    const config = (0, config_1.getConfig)();
    const resultDir = path_1.default.join(config.root, "results", testId);
    const tasks = result.datasets.map((ds, i) => analyzeDataset(ds, i, resultDir));
    await Promise.all(tasks);
}
/**
 * Entry point for `pixie-qa analyze <test_run_id>`.
 */
async function analyze(testId) {
    try {
        (0, testResult_1.loadTestResult)(testId);
    }
    catch {
        console.error(`Error: No test result found for ID '${testId}'`);
        return 1;
    }
    const result = (0, testResult_1.loadTestResult)(testId);
    console.log(`Analyzing ${result.datasets.length} dataset(s) for test run ${testId}...`);
    await analyzeAll(testId);
    const config = (0, config_1.getConfig)();
    const resultDir = path_1.default.join(config.root, "results", testId);
    console.log(`Analysis saved to ${resultDir}`);
    return 0;
}
//# sourceMappingURL=analyzeCommand.js.map