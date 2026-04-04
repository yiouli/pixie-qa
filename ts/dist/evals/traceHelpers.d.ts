/**
 * Convenience functions that extract an Evaluable from a trace tree.
 *
 * These are `fromTrace` callables for use with `runAndEvaluate`
 * and `assertPass`.
 */
import type { Evaluable } from "../storage/evaluable";
import type { ObservationNode } from "../storage/tree";
/**
 * Find the LLMSpan with the latest `endedAt` in the trace tree
 * and return it as an Evaluable.
 *
 * @throws if no LLMSpan exists in the trace.
 */
export declare function lastLlmCall(trace: ObservationNode[]): Evaluable;
/**
 * Return the first root node's span as Evaluable.
 *
 * @throws if the trace is empty.
 */
export declare function root(trace: ObservationNode[]): Evaluable;
//# sourceMappingURL=traceHelpers.d.ts.map