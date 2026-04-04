/**
 * Pre-made pass criteria for `assertPass`.
 *
 * Provides `ScoreThreshold`, a configurable criterion that checks
 * whether a sufficient fraction of test cases score above a threshold.
 */
import type { Evaluation } from "./evaluation";
/**
 * Criteria function type: receives results matrix, returns [passed, message].
 */
export type PassCriteria = (results: Evaluation[][]) => [boolean, string];
/**
 * Pass criteria: `pct` fraction of inputs must score >= `threshold`
 * on all evaluators.
 */
export declare class ScoreThreshold {
    readonly threshold: number;
    readonly pct: number;
    constructor(threshold?: number, pct?: number);
    /**
     * Evaluate the results matrix and return `[passed, message]`.
     *
     * @param results - Shape `[inputs][evaluators]`.
     */
    __call__(results: Evaluation[][]): [boolean, string];
}
//# sourceMappingURL=criteria.d.ts.map