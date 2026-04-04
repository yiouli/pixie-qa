/**
 * ObservationNode tree wrapper with traversal and LLM-friendly serialization.
 */
import type { LLMSpan, ObserveSpan } from "../instrumentation/spans";
/**
 * Tree node wrapping a span with children for hierarchical traversal.
 */
export declare class ObservationNode {
    readonly span: ObserveSpan | LLMSpan;
    children: ObservationNode[];
    constructor(span: ObserveSpan | LLMSpan);
    get spanId(): string;
    get traceId(): string;
    get parentSpanId(): string | null;
    /** Human-readable name: `name` for observe, `requestModel` for LLM. */
    get name(): string;
    get durationMs(): number;
    /** Return all nodes in the subtree where `node.name === name` (DFS). */
    find(name: string): ObservationNode[];
    /** Return all nodes in the subtree matching the span type (`"llm"` or `"observe"`). */
    findByType(spanType: "llm" | "observe"): ObservationNode[];
    /** Serialize the tree to an LLM-friendly indented outline. */
    toText(indent?: number): string;
    private _observeToText;
    private _llmToText;
}
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
export declare function buildTree(spans: ReadonlyArray<ObserveSpan | LLMSpan>): ObservationNode[];
//# sourceMappingURL=tree.d.ts.map