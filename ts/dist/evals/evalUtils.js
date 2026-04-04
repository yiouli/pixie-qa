"use strict";
/**
 * Higher-level eval utilities: runAndEvaluate, assertPass, assertDatasetPass.
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.EvalAssertionError = exports.DEFAULT_RUNNABLE_CONCURRENCY = void 0;
exports.runAndEvaluate = runAndEvaluate;
exports.assertPass = assertPass;
exports.assertDatasetPass = assertDatasetPass;
const evaluable_1 = require("../storage/evaluable");
const tree_1 = require("../storage/tree");
const criteria_1 = require("./criteria");
const evaluation_1 = require("./evaluation");
const traceCapture_1 = require("./traceCapture");
// ── Constants ────────────────────────────────────────────────────────────────
/**
 * Default max number of runnables executing concurrently within a
 * single `assertPass` / `assertDatasetPass` call.
 */
exports.DEFAULT_RUNNABLE_CONCURRENCY = 4;
// ── EvalAssertionError ───────────────────────────────────────────────────────
/**
 * Raised by `assertPass` when the pass criteria are not met.
 */
class EvalAssertionError extends Error {
    results;
    constructor(message, results) {
        super(message);
        this.name = "EvalAssertionError";
        this.results = results;
    }
}
exports.EvalAssertionError = EvalAssertionError;
// ── Internal helpers ─────────────────────────────────────────────────────────
function defaultPassCriteria(results) {
    const allScores = results.flatMap((row) => row.map((e) => e.score));
    const avg = allScores.length > 0
        ? allScores.reduce((a, b) => a + b, 0) / allScores.length
        : 0;
    const passed = allScores.every((s) => s >= 0.5);
    return [passed, `Average score: ${avg.toFixed(2)}, all >= 0.5: ${passed}`];
}
function getRunnableConcurrency() {
    const raw = process.env["PIXIE_RUNNABLE_CONCURRENCY"];
    if (raw !== undefined) {
        const parsed = parseInt(raw, 10);
        if (!isNaN(parsed))
            return parsed;
    }
    return exports.DEFAULT_RUNNABLE_CONCURRENCY;
}
async function runAndCapture(runnable, evalInput, opts) {
    const { handler } = await (0, traceCapture_1.captureTraces)(async () => {
        await Promise.resolve(runnable(evalInput));
    });
    if (handler.spans.length === 0) {
        throw new Error("No spans captured during runnable execution");
    }
    const traceTree = (0, tree_1.buildTree)(handler.spans);
    let evaluable;
    if (opts?.fromTrace) {
        evaluable = opts.fromTrace(traceTree);
    }
    else {
        evaluable = (0, evaluable_1.asEvaluable)(traceTree[0].span);
    }
    if (opts?.expectedOutput !== undefined) {
        evaluable = {
            evalInput: evaluable.evalInput,
            evalOutput: evaluable.evalOutput,
            evalMetadata: evaluable.evalMetadata,
            expectedOutput: opts.expectedOutput,
            evaluators: evaluable.evaluators,
            description: evaluable.description,
        };
    }
    return [evaluable, traceTree];
}
// ── runAndEvaluate ───────────────────────────────────────────────────────────
/**
 * Run a runnable while capturing traces, then evaluate.
 *
 * The runnable is called exactly once.
 */
async function runAndEvaluate(evaluator, runnable, evalInput, opts) {
    const [evaluable, traceTree] = await runAndCapture(runnable, evalInput, opts);
    return (0, evaluation_1.evaluate)(evaluator, evaluable, { trace: traceTree });
}
// ── processSingleInput ───────────────────────────────────────────────────────
async function processSingleInput(idx, inp, evaluators, evaluables, runnable, fromTrace, semaphore) {
    const runRunnable = async () => {
        const captureOpts = {};
        if (evaluables !== null) {
            captureOpts.expectedOutput = evaluables[idx].expectedOutput;
        }
        if (fromTrace) {
            captureOpts.fromTrace = fromTrace;
        }
        if (semaphore) {
            await semaphore.acquire();
            try {
                return await runAndCapture(runnable, inp, captureOpts);
            }
            finally {
                semaphore.release();
            }
        }
        return runAndCapture(runnable, inp, captureOpts);
    };
    if (evaluables !== null) {
        const evItem = evaluables[idx];
        if (evItem.evalOutput === null) {
            const [evaluable, traceTree] = await runRunnable();
            const evalPromises = evaluators.map((ev) => (0, evaluation_1.evaluate)(ev, evaluable, { trace: traceTree }));
            return Promise.all(evalPromises);
        }
        else {
            const evalPromises = evaluators.map((ev) => (0, evaluation_1.evaluate)(ev, evItem));
            return Promise.all(evalPromises);
        }
    }
    else {
        const [evaluable, traceTree] = await runRunnable();
        const evalPromises = evaluators.map((ev) => (0, evaluation_1.evaluate)(ev, evaluable, { trace: traceTree }));
        return Promise.all(evalPromises);
    }
}
// ── Semaphore utility ────────────────────────────────────────────────────────
function createSemaphore(max) {
    let count = 0;
    const queue = [];
    return {
        acquire() {
            if (count < max) {
                count++;
                return Promise.resolve();
            }
            return new Promise((resolve) => queue.push(resolve));
        },
        release() {
            const next = queue.shift();
            if (next) {
                next();
            }
            else {
                count--;
            }
        },
    };
}
// ── assertPass ───────────────────────────────────────────────────────────────
/**
 * Run evaluators against a runnable over multiple inputs.
 *
 * The results matrix has shape `[evalInputs][evaluators]`.
 * If the pass criteria are not met, throws `EvalAssertionError`.
 */
async function assertPass(runnable, evalInputs, evaluators, opts) {
    const evaluables = opts?.evaluables ?? null;
    if (evaluables !== null && evaluables.length !== evalInputs.length) {
        throw new Error(`evaluables length (${evaluables.length}) must match evalInputs length (${evalInputs.length})`);
    }
    const defaultCriteria = new criteria_1.ScoreThreshold();
    const criteria = opts?.passCriteria ?? defaultCriteria.__call__.bind(defaultCriteria);
    const sem = createSemaphore(getRunnableConcurrency());
    const inputTasks = evalInputs.map((inp, idx) => processSingleInput(idx, inp, evaluators, evaluables, runnable, opts?.fromTrace, sem));
    const results = await Promise.all(inputTasks);
    const [passed, message] = criteria(results);
    if (!passed) {
        throw new EvalAssertionError(message, results);
    }
}
// ── assertDatasetPass ────────────────────────────────────────────────────────
/**
 * Load a dataset by name, then run `assertPass` with its items.
 */
async function assertDatasetPass(runnable, datasetName, evaluators, opts) {
    const { DatasetStore } = await Promise.resolve().then(() => __importStar(require("../dataset/store")));
    const store = new DatasetStore(opts?.datasetDir);
    const dataset = store.get(datasetName);
    const items = [...dataset.items];
    const evalInputs = items.map((item) => item.evalInput);
    await assertPass(runnable, evalInputs, evaluators, {
        evaluables: items,
        passCriteria: opts?.passCriteria,
        fromTrace: opts?.fromTrace,
    });
}
//# sourceMappingURL=evalUtils.js.map