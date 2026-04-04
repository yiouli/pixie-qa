"use strict";
/**
 * ObservationNode tree wrapper with traversal and LLM-friendly serialization.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ObservationNode = void 0;
exports.buildTree = buildTree;
// ── ObservationNode ──────────────────────────────────────────────────────────
/**
 * Tree node wrapping a span with children for hierarchical traversal.
 */
class ObservationNode {
    span;
    children;
    constructor(span) {
        this.span = span;
        this.children = [];
    }
    // ── Delegated properties ──────────────────────────────────────────────
    get spanId() {
        return this.span.spanId;
    }
    get traceId() {
        return this.span.traceId;
    }
    get parentSpanId() {
        return this.span.parentSpanId;
    }
    /** Human-readable name: `name` for observe, `requestModel` for LLM. */
    get name() {
        if ("operation" in this.span) {
            return this.span.requestModel;
        }
        return this.span.name ?? "(unnamed)";
    }
    get durationMs() {
        return this.span.durationMs;
    }
    // ── Search ────────────────────────────────────────────────────────────
    /** Return all nodes in the subtree where `node.name === name` (DFS). */
    find(name) {
        const result = [];
        if (this.name === name) {
            result.push(this);
        }
        for (const child of this.children) {
            result.push(...child.find(name));
        }
        return result;
    }
    /** Return all nodes in the subtree matching the span type (`"llm"` or `"observe"`). */
    findByType(spanType) {
        const result = [];
        const isMatch = spanType === "llm"
            ? "operation" in this.span
            : !("operation" in this.span);
        if (isMatch) {
            result.push(this);
        }
        for (const child of this.children) {
            result.push(...child.findByType(spanType));
        }
        return result;
    }
    // ── Serialization ─────────────────────────────────────────────────────
    /** Serialize the tree to an LLM-friendly indented outline. */
    toText(indent = 0) {
        const prefix = "  ".repeat(indent);
        if ("operation" in this.span) {
            return this._llmToText(prefix, indent);
        }
        return this._observeToText(prefix, indent);
    }
    _observeToText(prefix, indent) {
        const span = this.span;
        const lines = [];
        const name = span.name ?? "(unnamed)";
        lines.push(`${prefix}${name} [${span.durationMs.toFixed(0)}ms]`);
        if (span.input !== null && span.input !== undefined) {
            lines.push(`${prefix}  input: ${formatValue(span.input)}`);
        }
        if (span.output !== null && span.output !== undefined) {
            lines.push(`${prefix}  output: ${formatValue(span.output)}`);
        }
        if (span.error !== null) {
            lines.push(`${prefix}  <e>${span.error}</e>`);
        }
        if (span.metadata && Object.keys(span.metadata).length > 0) {
            lines.push(`${prefix}  metadata: ${JSON.stringify(span.metadata)}`);
        }
        for (const child of this.children) {
            lines.push(child.toText(indent + 1));
        }
        return lines.join("\n");
    }
    _llmToText(prefix, indent) {
        const span = this.span;
        const lines = [];
        lines.push(`${prefix}${span.requestModel} [${span.provider}, ${span.durationMs.toFixed(0)}ms]`);
        // Input messages
        if (span.inputMessages.length > 0) {
            lines.push(`${prefix}  input_messages:`);
            for (const msg of span.inputMessages) {
                lines.push(`${prefix}    ${formatMessage(msg)}`);
            }
        }
        // Output messages
        if (span.outputMessages.length > 0) {
            lines.push(`${prefix}  output:`);
            for (const msg of span.outputMessages) {
                lines.push(`${prefix}    ${formatMessage(msg)}`);
            }
        }
        // Tokens
        const tokenParts = [];
        if (span.inputTokens > 0 || span.outputTokens > 0) {
            tokenParts.push(`${span.inputTokens} in / ${span.outputTokens} out`);
            if (span.cacheReadTokens > 0) {
                tokenParts.push(`(${span.cacheReadTokens} cache read)`);
            }
            if (span.cacheCreationTokens > 0) {
                tokenParts.push(`(${span.cacheCreationTokens} cache creation)`);
            }
            lines.push(`${prefix}  tokens: ${tokenParts.join(" ")}`);
        }
        // Error
        if (span.errorType !== null) {
            lines.push(`${prefix}  <e>${span.errorType}</e>`);
        }
        // Tool definitions
        if (span.toolDefinitions.length > 0) {
            const toolNames = span.toolDefinitions.map((td) => td.name).join(", ");
            lines.push(`${prefix}  tools: [${toolNames}]`);
        }
        for (const child of this.children) {
            lines.push(child.toText(indent + 1));
        }
        return lines.join("\n");
    }
}
exports.ObservationNode = ObservationNode;
// ── Helpers ──────────────────────────────────────────────────────────────────
function formatValue(value) {
    if (typeof value === "object" && value !== null) {
        return JSON.stringify(value);
    }
    return String(value);
}
function formatMessage(msg) {
    if (msg.role === "system") {
        return `system: ${msg.content}`;
    }
    if (msg.role === "user") {
        const parts = msg.content
            .filter((p) => p.type === "text")
            .map((p) => p.text);
        return `user: ${parts.join("")}`;
    }
    if (msg.role === "assistant") {
        const aMsg = msg;
        const parts = aMsg.content
            .filter((p) => p.type === "text")
            .map((p) => p.text);
        let text = `assistant: ${parts.join("")}`;
        if (aMsg.toolCalls.length > 0) {
            const names = aMsg.toolCalls.map((tc) => tc.name).join(", ");
            text += ` [tool_calls: ${names}]`;
        }
        return text;
    }
    if (msg.role === "tool") {
        const tMsg = msg;
        return `tool(${tMsg.toolName}): ${tMsg.content}`;
    }
    return String(msg);
}
// ── Tree builder ─────────────────────────────────────────────────────────────
/**
 * Build a tree from a flat list of spans sharing the same trace.
 *
 * Algorithm:
 * 1. Create an `ObservationNode` for each span.
 * 2. Index by `span.spanId`.
 * 3. Link children to parents via `parentSpanId`.
 * 4. Orphaned nodes (missing parent) become roots.
 * 5. Sort each node's children by `startedAt` ascending.
 * 6. Return sorted list of root nodes.
 */
function buildTree(spans) {
    const nodes = new Map();
    for (const span of spans) {
        nodes.set(span.spanId, new ObservationNode(span));
    }
    const roots = [];
    for (const node of nodes.values()) {
        const pid = node.span.parentSpanId;
        if (pid !== null && nodes.has(pid)) {
            nodes.get(pid).children.push(node);
        }
        else {
            roots.push(node);
        }
    }
    // Sort children by startedAt
    for (const node of nodes.values()) {
        node.children.sort((a, b) => a.span.startedAt.getTime() - b.span.startedAt.getTime());
    }
    roots.sort((a, b) => a.span.startedAt.getTime() - b.span.startedAt.getTime());
    return roots;
}
//# sourceMappingURL=tree.js.map