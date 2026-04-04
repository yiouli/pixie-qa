"use strict";
/**
 * Convenience functions that extract an Evaluable from a trace tree.
 *
 * These are `fromTrace` callables for use with `runAndEvaluate`
 * and `assertPass`.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.lastLlmCall = lastLlmCall;
exports.root = root;
const evaluable_1 = require("../storage/evaluable");
// ── Helpers ──────────────────────────────────────────────────────────────────
function flatten(nodes) {
    const result = [];
    for (const node of nodes) {
        result.push(node);
        result.push(...flatten(node.children));
    }
    return result;
}
// ── Public API ───────────────────────────────────────────────────────────────
/**
 * Find the LLMSpan with the latest `endedAt` in the trace tree
 * and return it as an Evaluable.
 *
 * @throws if no LLMSpan exists in the trace.
 */
function lastLlmCall(trace) {
    const allNodes = flatten(trace);
    const llmNodes = allNodes.filter((n) => "operation" in n.span);
    if (llmNodes.length === 0) {
        throw new Error("No LLMSpan found in the trace");
    }
    llmNodes.sort((a, b) => b.span.endedAt.getTime() -
        a.span.endedAt.getTime());
    return (0, evaluable_1.asEvaluable)(llmNodes[0].span);
}
/**
 * Return the first root node's span as Evaluable.
 *
 * @throws if the trace is empty.
 */
function root(trace) {
    if (trace.length === 0) {
        throw new Error("Trace is empty");
    }
    return (0, evaluable_1.asEvaluable)(trace[0].span);
}
//# sourceMappingURL=traceHelpers.js.map