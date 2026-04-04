/**
 * Validate a captured trace tree against a data-flow DAG.
 */

import type { ObservationNode } from "../storage/tree";
import type { DagNode } from "./index";
import { isValidDagName, parseDag } from "./index";

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
 * Recursively collect span name and type info from a trace tree.
 */
function collectSpanInfo(
  nodes: ObservationNode[]
): Array<{ name: string; type: string }> {
  const info: Array<{ name: string; type: string }> = [];
  for (const node of nodes) {
    const spanType = "operation" in node.span ? "llm_call" : "observation";
    info.push({ name: node.name, type: spanType });
    info.push(...collectSpanInfo(node.children));
  }
  return info;
}

/**
 * Check that the trace tree contains spans matching the DAG nodes.
 *
 * Matching rules:
 * - If `isLlmCall` is true on a DAG node, the check passes when at
 *   least one LLM span exists in the trace. Name matching is skipped.
 * - Otherwise, the DAG node name must match a non-LLM span name exactly.
 */
export function checkTraceAgainstDag(
  dagNodes: DagNode[],
  traceTree: ObservationNode[]
): TraceCheckResult {
  const result: TraceCheckResult = {
    valid: true,
    matched: [],
    unmatched: [],
    extraSpans: [],
    errors: [],
  };
  const unmatchedReasons = new Map<string, string>();

  // Enforce naming contract
  const invalidNames: string[] = [];
  for (const node of dagNodes) {
    if (!isValidDagName(node.name)) {
      invalidNames.push(
        `DAG node '${node.name}': name must be lower_snake_case (e.g., 'handle_turn').`
      );
    }
    if (node.parent !== null && !isValidDagName(node.parent)) {
      invalidNames.push(
        `DAG node '${node.name}': parent '${node.parent}' must be lower_snake_case.`
      );
    }
  }
  if (invalidNames.length > 0) {
    return { valid: false, matched: [], unmatched: [], extraSpans: [], errors: invalidNames };
  }

  // Collect spans from trace
  const spanInfo = collectSpanInfo(traceTree);
  const spanNamesByType: Record<string, Set<string>> = {
    observation: new Set<string>(),
    llm_call: new Set<string>(),
  };
  for (const span of spanInfo) {
    if (!spanNamesByType[span.type]) {
      spanNamesByType[span.type] = new Set();
    }
    spanNamesByType[span.type].add(span.name);
  }

  const spanNames = new Set([
    ...spanNamesByType["observation"],
    ...spanNamesByType["llm_call"],
  ]);
  const hasLlmSpans = spanInfo.some((s) => s.type === "llm_call");
  const hasLlmDagNodes = dagNodes.some((n) => n.isLlmCall);

  // Check each DAG node has a matching span
  const matchedSpanNames = new Set<string>();
  for (const dagNode of dagNodes) {
    if (dagNode.isLlmCall) {
      if (hasLlmSpans) {
        result.matched.push(dagNode.name);
      } else {
        result.unmatched.push(dagNode.name);
        unmatchedReasons.set(dagNode.name, "missing_llm_span");
      }
      continue;
    }

    if (!spanNames.has(dagNode.name)) {
      result.unmatched.push(dagNode.name);
      unmatchedReasons.set(dagNode.name, "missing_named_span");
      continue;
    }

    // For non-LLM DAG nodes, ensure the matched span is non-LLM
    if (
      spanNamesByType["llm_call"].has(dagNode.name) &&
      !spanNamesByType["observation"].has(dagNode.name)
    ) {
      result.unmatched.push(dagNode.name);
      unmatchedReasons.set(dagNode.name, "llm_flag_mismatch");
    } else {
      result.matched.push(dagNode.name);
      matchedSpanNames.add(dagNode.name);
    }
  }

  // Find spans not accounted for by the DAG
  for (const spanName of [...spanNamesByType["observation"]].sort()) {
    if (!matchedSpanNames.has(spanName)) {
      result.extraSpans.push(spanName);
    }
  }
  if (!hasLlmDagNodes) {
    for (const spanName of [...spanNamesByType["llm_call"]].sort()) {
      result.extraSpans.push(spanName);
    }
  }

  if (result.unmatched.length > 0) {
    result.valid = false;
    for (const nodeName of result.unmatched) {
      const node = dagNodes.find((n) => n.name === nodeName)!;
      const reason = unmatchedReasons.get(nodeName);
      if (reason === "missing_llm_span") {
        result.errors.push(
          `DAG node '${node.name}' (is_llm_call=true) expects at least ` +
          `one LLM span in the trace, but none were found. ` +
          `Common fix: ensure \`enableStorage()\` is called BEFORE the ` +
          `LLM client (OpenAI, Anthropic, etc.) is created.`
        );
      } else if (reason === "llm_flag_mismatch") {
        result.errors.push(
          `DAG node '${node.name}' has is_llm_call=false but matched an LLM ` +
          `span. Fix: set \`isLlmCall: true\` on this node in the DAG JSON.`
        );
      } else {
        result.errors.push(
          `DAG node '${node.name}' has no matching span in the trace. ` +
          `This means either: (1) the function at \`codePointer\` is not ` +
          `decorated with \`observe(fn, '${node.name}')\`, or (2) the ` +
          `function was not called during the trace run. Fix: wrap the function ` +
          `with \`observe(fn, '${node.name}')\`, or if already wrapped, ensure ` +
          `the name matches exactly.`
        );
      }
    }
  }

  return result;
}

/**
 * Load the most recent trace and check it against a DAG JSON file.
 *
 * Returns a TraceCheckResult with match details.
 */
export async function checkLastTrace(
  dagJsonPath: string
): Promise<TraceCheckResult> {
  const { getConfig } = await import("../config");
  const { ObservationStore } = await import("../storage/store");

  // Parse DAG
  const [dagNodes, parseErrors] = parseDag(dagJsonPath);
  if (parseErrors.length > 0) {
    return { valid: false, matched: [], unmatched: [], extraSpans: [], errors: parseErrors };
  }

  // Load latest trace
  const config = getConfig();
  const store = new ObservationStore(config.dbPath);
  try {
    store.createTables();
    const traces = store.listTraces(1);
    if (traces.length === 0) {
      return {
        valid: false,
        matched: [],
        unmatched: [],
        extraSpans: [],
        errors: ["No traces found. Run the app first to produce a trace."],
      };
    }

    const traceId = traces[0]["traceId"] as string;
    const tree = store.getTrace(traceId);
    if (tree.length === 0) {
      return {
        valid: false,
        matched: [],
        unmatched: [],
        extraSpans: [],
        errors: [`No spans found for trace '${traceId}'.`],
      };
    }

    return checkTraceAgainstDag(dagNodes, tree);
  } finally {
    store.close();
  }
}
