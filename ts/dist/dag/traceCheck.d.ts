/**
 * Validate a captured trace tree against a data-flow DAG.
 */
import type { ObservationNode } from "../storage/tree";
import type { DagNode } from "./index";
/** Result of checking a trace against the DAG. */
export interface TraceCheckResult {
    valid: boolean;
    /** DAG node names that matched. */
    matched: string[];
    /** DAG node names not found in trace. */
    unmatched: string[];
    /** Span names not in DAG. */
    extraSpans: string[];
    errors: string[];
}
/**
 * Check that the trace tree contains spans matching the DAG nodes.
 *
 * Matching rules:
 * - If `isLlmCall` is true on a DAG node, the check passes when at
 *   least one LLM span exists in the trace. Name matching is skipped.
 * - Otherwise, the DAG node name must match a non-LLM span name exactly.
 */
export declare function checkTraceAgainstDag(dagNodes: DagNode[], traceTree: ObservationNode[]): TraceCheckResult;
/**
 * Load the most recent trace and check it against a DAG JSON file.
 *
 * Returns a TraceCheckResult with match details.
 */
export declare function checkLastTrace(dagJsonPath: string): Promise<TraceCheckResult>;
//# sourceMappingURL=traceCheck.d.ts.map