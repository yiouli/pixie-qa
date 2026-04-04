/**
 * Convenience functions that extract an Evaluable from a trace tree.
 *
 * These are `fromTrace` callables for use with `runAndEvaluate`
 * and `assertPass`.
 */

import type { LLMSpan } from "../instrumentation/spans";
import type { Evaluable } from "../storage/evaluable";
import { asEvaluable } from "../storage/evaluable";
import type { ObservationNode } from "../storage/tree";

// ── Helpers ──────────────────────────────────────────────────────────────────

function flatten(nodes: ObservationNode[]): ObservationNode[] {
  const result: ObservationNode[] = [];
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
export function lastLlmCall(trace: ObservationNode[]): Evaluable {
  const allNodes = flatten(trace);
  const llmNodes = allNodes.filter(
    (n) => "operation" in n.span
  );
  if (llmNodes.length === 0) {
    throw new Error("No LLMSpan found in the trace");
  }
  llmNodes.sort(
    (a, b) =>
      (b.span as LLMSpan).endedAt.getTime() -
      (a.span as LLMSpan).endedAt.getTime()
  );
  return asEvaluable(llmNodes[0].span);
}

/**
 * Return the first root node's span as Evaluable.
 *
 * @throws if the trace is empty.
 */
export function root(trace: ObservationNode[]): Evaluable {
  if (trace.length === 0) {
    throw new Error("Trace is empty");
  }
  return asEvaluable(trace[0].span);
}
