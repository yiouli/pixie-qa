/**
 * `pixie-qa trace` CLI subcommands — list, show, last, verify.
 *
 * Provides read-only inspection of captured traces via the ObservationStore.
 */

import type { ObservationNode } from "../storage/tree";
import type { LLMSpan } from "../instrumentation/spans";
import { ObservationStore } from "../storage/store";
import { getConfig } from "../config";

function makeStore(): ObservationStore {
  const config = getConfig();
  const store = new ObservationStore(config.dbPath);
  store.createTables();
  return store;
}

function formatDatetime(value: unknown): string {
  if (value instanceof Date) {
    return value.toISOString().replace("T", " ").substring(0, 16);
  }
  if (typeof value === "string") {
    try {
      const dt = new Date(value);
      return dt.toISOString().replace("T", " ").substring(0, 16);
    } catch {
      return value;
    }
  }
  return value != null ? String(value) : "";
}

function compactText(node: ObservationNode, indent: number = 0): string {
  const prefix = "  ".repeat(indent);
  const lines: string[] = [];

  if ("operation" in node.span) {
    const span = node.span as LLMSpan;
    lines.push(
      `${prefix}${span.requestModel} [${span.provider}, ${span.durationMs.toFixed(0)}ms]`
    );
    if (span.inputTokens > 0 || span.outputTokens > 0) {
      lines.push(
        `${prefix}  tokens: ${span.inputTokens} in / ${span.outputTokens} out`
      );
    }
  } else {
    const name = node.span.name ?? "(unnamed)";
    lines.push(`${prefix}${name} [${node.span.durationMs.toFixed(0)}ms]`);
  }

  for (const child of node.children) {
    lines.push(compactText(child, indent + 1));
  }
  return lines.join("\n");
}

function countNodes(tree: ObservationNode[]): number {
  let count = 0;
  for (const node of tree) {
    count += 1 + countNodes(node.children);
  }
  return count;
}

/**
 * Entry point for `pixie-qa trace list`.
 */
export function traceList(
  limit: number = 10,
  errorsOnly: boolean = false
): number {
  const store = makeStore();
  try {
    let traces = store.listTraces(limit);
    if (errorsOnly) {
      traces = traces.filter((t) => t["hasError"]);
    }

    if (traces.length === 0) {
      console.log("No traces found.");
      return 0;
    }

    const header =
      `${"TRACE_ID".padEnd(34)}` +
      `${"ROOT SPAN".padEnd(25)}` +
      `${"STARTED".padEnd(20)}` +
      `${"SPANS".padStart(6)}` +
      `${"ERRORS".padStart(7)}`;
    console.log(header);
    for (const t of traces) {
      const row =
        `${String(t["traceId"]).padEnd(34)}` +
        `${String(t["rootName"] ?? "(unknown)").padEnd(25)}` +
        `${formatDatetime(t["startedAt"]).padEnd(20)}` +
        `${String(t["observationCount"] ?? 0).padStart(6)}` +
        `${(t["hasError"] ? "yes" : "").padStart(7)}`;
      console.log(row);
    }
    return 0;
  } finally {
    store.close();
  }
}

/**
 * Entry point for `pixie-qa trace show`.
 */
export function traceShow(
  traceId: string,
  verbose: boolean = false,
  asJson: boolean = false
): number {
  const store = makeStore();
  try {
    // Support prefix matching
    const traces = store.listTraces(500);
    const matched = traces.filter((t) =>
      String(t["traceId"]).startsWith(traceId)
    );
    if (matched.length === 0) {
      console.log(`Error: No trace found matching '${traceId}'`);
      return 1;
    }
    if (matched.length > 1) {
      const ids = matched
        .slice(0, 10)
        .map((t) => String(t["traceId"]))
        .join("\n  ");
      console.log(
        `Error: Multiple traces match '${traceId}'. Be more specific:\n  ${ids}`
      );
      return 1;
    }
    const fullId = String(matched[0]["traceId"]);

    const tree = store.getTrace(fullId);
    if (tree.length === 0) {
      console.log(`Error: No spans found for trace '${fullId}'`);
      return 1;
    }

    if (asJson) {
      const { serializeSpan } = require("../storage/serialization");
      const spansData: unknown[] = [];
      const collectSerialized = (node: ObservationNode): void => {
        spansData.push(serializeSpan(node.span));
        for (const child of node.children) {
          collectSerialized(child);
        }
      };
      for (const root of tree) {
        collectSerialized(root);
      }
      console.log(JSON.stringify(spansData, null, 2));
      return 0;
    }

    if (verbose) {
      const lines = [`[trace_id: ${fullId}]\n`];
      for (const rootNode of tree) {
        lines.push(rootNode.toText(0));
      }
      console.log(lines.join("\n"));
    } else {
      const lines = [`[trace_id: ${fullId}]\n`];
      for (const rootNode of tree) {
        lines.push(compactText(rootNode, 0));
      }
      console.log(lines.join("\n"));
    }
    return 0;
  } finally {
    store.close();
  }
}

/**
 * Entry point for `pixie-qa trace last`.
 */
export function traceLast(asJson: boolean = false): number {
  const store = makeStore();
  try {
    const traces = store.listTraces(1);
    if (traces.length === 0) {
      console.log("No traces found.");
      return 0;
    }
    const traceId = String(traces[0]["traceId"]);
    return traceShow(traceId, true, asJson);
  } finally {
    store.close();
  }
}

/**
 * Entry point for `pixie-qa trace verify`.
 */
export function traceVerify(): number {
  const store = makeStore();
  try {
    const traces = store.listTraces(1);
    if (traces.length === 0) {
      console.log(
        "ERROR: No traces found. Run the app first to produce a trace."
      );
      return 1;
    }

    const traceId = String(traces[0]["traceId"]);
    const tree = store.getTrace(traceId);
    if (tree.length === 0) {
      console.log(`ERROR: No spans found for trace '${traceId}'.`);
      return 1;
    }

    const lines: string[] = [];
    const issues: string[] = [];

    lines.push(`Trace: ${traceId}`);
    lines.push(`Spans: ${countNodes(tree)}`);
    lines.push("");

    // Check 1: Root span should be an @observe span
    const rootNode = tree[0];
    const rootIsLlm = "operation" in rootNode.span;
    if (rootIsLlm) {
      issues.push(
        "Root span is an LLM call, not an observe-wrapped function. " +
        "Ensure enableStorage() is called BEFORE the observe function runs."
      );
      lines.push(`Root span: ${rootNode.name} (LLM) <- WRONG`);
    } else {
      lines.push(`Root span: ${rootNode.name} (observe) <- OK`);
    }

    // Check 2: Root span has input and output
    if (!rootIsLlm) {
      const rootObserve = rootNode.span;
      const hasInput = (rootObserve as { input?: unknown }).input != null;
      const hasOutput = (rootObserve as { output?: unknown }).output != null;
      if (!hasInput) {
        issues.push(
          "Root span input is null. The observe-wrapped function's " +
          "arguments are not being captured."
        );
        lines.push("Root input:  null <- MISSING");
      } else {
        lines.push("Root input:  present <- OK");
      }
      if (!hasOutput) {
        issues.push(
          "Root span output is null. The observe-wrapped function's " +
          "return value is not being captured."
        );
        lines.push("Root output: null <- MISSING");
      } else {
        lines.push("Root output: present <- OK");
      }
    }

    // Check 3: LLM child spans
    let llmCount = 0;
    for (const root of tree) {
      llmCount += root.findByType("llm").length;
    }
    if (llmCount === 0) {
      issues.push(
        "No LLM child spans found. Ensure enableStorage() is called " +
        "so that LLM provider calls (OpenAI, Anthropic) are auto-captured."
      );
      lines.push("LLM spans:   0 <- MISSING");
    } else {
      lines.push(`LLM spans:   ${llmCount} <- OK`);
    }

    lines.push("");
    lines.push("Span tree:");
    for (const root of tree) {
      lines.push(compactText(root, 1));
    }
    lines.push("");

    if (issues.length > 0) {
      lines.push(`FAILED — ${issues.length} issue(s):`);
      for (let i = 0; i < issues.length; i++) {
        lines.push(`  ${i + 1}. ${issues[i]}`);
      }
      console.log(lines.join("\n"));
      return 1;
    }

    lines.push("PASSED — trace looks good.");
    console.log(lines.join("\n"));
    return 0;
  } finally {
    store.close();
  }
}
