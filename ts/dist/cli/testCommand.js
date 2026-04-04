"use strict";
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
exports.testMain = testMain;
const path_1 = __importDefault(require("path"));
const datasetRunner_1 = require("../evals/datasetRunner");
const evaluation_1 = require("../evals/evaluation");
const testResult_1 = require("../evals/testResult");
const config_1 = require("../config");
/**
 * Run evaluations for a single dataset and return a DatasetResult.
 */
async function runDataset(datasetPath) {
    const loaded = (0, datasetRunner_1.loadDatasetEntries)(datasetPath);
    const entryResults = [];
    for (const [evaluable, evaluatorNames] of loaded.entries) {
        // Resolve evaluators dynamically
        const evaluators = [];
        const shortNames = [];
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
                }
                else {
                    evaluators.push(cls);
                }
            }
            catch {
                // If evaluator can't be resolved, create a stub that returns 0
                evaluators.push(() => ({
                    score: 0,
                    reasoning: `Could not resolve evaluator: ${name}`,
                    details: {},
                }));
            }
        }
        const evals = [];
        for (const ev of evaluators) {
            const result = await (0, evaluation_1.evaluate)(ev, evaluable);
            evals.push(result);
        }
        const expOut = evaluable.expectedOutput;
        const expectedOutput = typeof expOut === "symbol" || expOut === null ? null : expOut;
        const evalResults = shortNames.map((name, i) => ({
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
async function testMain(opts) {
    const config = (0, config_1.getConfig)();
    const searchPath = opts.path ?? config.datasetDir;
    const datasetFiles = (0, datasetRunner_1.discoverDatasetFiles)(searchPath);
    if (datasetFiles.length === 0) {
        console.log("No dataset files found.");
        return 1;
    }
    const commandStr = "pixie-qa test " + (opts.path ?? "");
    const testId = (0, testResult_1.generateTestId)();
    const startedAt = new Date().toISOString();
    let allPassed = true;
    const datasetResults = [];
    for (const dsPath of datasetFiles) {
        let dsResult;
        try {
            dsResult = await runDataset(path_1.default.resolve(dsPath));
        }
        catch (exc) {
            console.log(String(exc));
            return 1;
        }
        datasetResults.push(dsResult);
        // Print results
        const passedCount = dsResult.entries.filter((entry) => entry.evaluations.every((ev) => ev.score >= 0.5)).length;
        const totalCount = dsResult.entries.length;
        console.log(`\n${"=".repeat(52)} ${dsResult.dataset} ${"=".repeat(52)}`);
        for (let i = 0; i < dsResult.entries.length; i++) {
            const entry = dsResult.entries[i];
            const evalsStr = entry.evaluations.map((ev) => ev.evaluator).join(", ");
            const scores = entry.evaluations.map((ev) => ev.score.toFixed(2));
            const allPass = entry.evaluations.every((ev) => ev.score >= 0.5);
            const mark = allPass ? "\u2713" : "\u2717";
            let desc = entry.description ?? JSON.stringify(entry.input);
            if (desc.length > 80)
                desc = desc.substring(0, 80) + "\u2026";
            console.log(`  [${i + 1}] ${desc} (${evalsStr}) [${scores.join(", ")}] ${mark}`);
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
    const runResult = {
        testId,
        command: commandStr,
        startedAt,
        endedAt,
        datasets: datasetResults,
    };
    const resultPath = (0, testResult_1.saveTestResult)(runResult);
    console.log(`\nResults saved to ${resultPath}`);
    if (!opts.noOpen) {
        try {
            const { openWebui } = await Promise.resolve().then(() => __importStar(require("../web/server")));
            await openWebui(config.root, {
                tab: "results",
                itemId: `results/${testId}`,
            });
        }
        catch {
            // Web UI opening is best-effort
        }
    }
    return allPassed ? 0 : 1;
}
//# sourceMappingURL=testCommand.js.map