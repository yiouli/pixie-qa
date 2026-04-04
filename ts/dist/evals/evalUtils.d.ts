/**
 * Higher-level eval utilities: runAndEvaluate, assertPass, assertDatasetPass.
 */
import type { Evaluable } from "../storage/evaluable";
import type { ObservationNode } from "../storage/tree";
import { type PassCriteria } from "./criteria";
import type { Evaluation, Evaluator } from "./evaluation";
/**
 * Default max number of runnables executing concurrently within a
 * single `assertPass` / `assertDatasetPass` call.
 */
export declare const DEFAULT_RUNNABLE_CONCURRENCY = 4;
/**
 * Raised by `assertPass` when the pass criteria are not met.
 */
export declare class EvalAssertionError extends Error {
    readonly results: Evaluation[][];
    constructor(message: string, results: Evaluation[][]);
}
type Runnable = (evalInput: unknown) => unknown | Promise<unknown>;
type FromTrace = (trace: ObservationNode[]) => Evaluable;
/**
 * Run a runnable while capturing traces, then evaluate.
 *
 * The runnable is called exactly once.
 */
export declare function runAndEvaluate(evaluator: Evaluator, runnable: Runnable, evalInput: unknown, opts?: {
    expectedOutput?: unknown;
    fromTrace?: FromTrace;
}): Promise<Evaluation>;
/**
 * Run evaluators against a runnable over multiple inputs.
 *
 * The results matrix has shape `[evalInputs][evaluators]`.
 * If the pass criteria are not met, throws `EvalAssertionError`.
 */
export declare function assertPass(runnable: Runnable, evalInputs: unknown[], evaluators: Evaluator[], opts?: {
    evaluables?: Evaluable[];
    passCriteria?: PassCriteria;
    fromTrace?: FromTrace;
}): Promise<void>;
/**
 * Load a dataset by name, then run `assertPass` with its items.
 */
export declare function assertDatasetPass(runnable: Runnable, datasetName: string, evaluators: Evaluator[], opts?: {
    datasetDir?: string;
    passCriteria?: PassCriteria;
    fromTrace?: FromTrace;
}): Promise<void>;
export {};
//# sourceMappingURL=evalUtils.d.ts.map