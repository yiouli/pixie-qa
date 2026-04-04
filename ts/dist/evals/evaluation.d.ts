/**
 * Evaluation primitives: Evaluation result, Evaluator type, evaluate().
 */
import type { Evaluable } from "../storage/evaluable";
import type { ObservationNode } from "../storage/tree";
/**
 * The result of a single evaluator applied to a single test case.
 */
export interface Evaluation {
    readonly score: number;
    readonly reasoning: string;
    readonly details: Record<string, unknown>;
}
/**
 * Create an Evaluation with default empty details.
 */
export declare function createEvaluation(opts: {
    score: number;
    reasoning: string;
    details?: Record<string, unknown>;
}): Evaluation;
/**
 * An evaluator is any callable matching this signature.
 *
 * Both sync and async functions are supported; sync evaluators are
 * wrapped automatically.
 */
export type Evaluator = (evaluable: Evaluable, opts?: {
    trace?: ObservationNode[];
}) => Evaluation | Promise<Evaluation>;
/**
 * Run a single evaluator against a single evaluable.
 *
 * - Calls evaluator with `evaluable` and optional `trace`.
 * - Clamps returned `score` to [0.0, 1.0].
 * - Applies rate limiting if configured.
 * - Evaluator errors propagate unchanged.
 */
export declare function evaluate(evaluator: Evaluator, evaluable: Evaluable, opts?: {
    trace?: ObservationNode[];
}): Promise<Evaluation>;
//# sourceMappingURL=evaluation.d.ts.map