/**
 * ObservationStore — synchronous persistence and query API using better-sqlite3.
 *
 * Since better-sqlite3 is a synchronous driver, all methods are sync
 * (unlike the async Python version using Piccolo).
 */
import type { LLMSpan, ObserveSpan } from "../instrumentation/spans";
import { ObservationNode } from "./tree";
export declare class ObservationStore {
    private _db;
    constructor(dbPath: string);
    /** Create the observation table if it does not exist. */
    createTables(): void;
    /** Serialize and insert a single span. */
    save(span: ObserveSpan | LLMSpan): void;
    /** Batch insert multiple spans (uses a transaction). */
    saveMany(spans: ReadonlyArray<ObserveSpan | LLMSpan>): void;
    /** Return the trace as a tree of ObservationNode instances. */
    getTrace(traceId: string): ObservationNode[];
    /** Return all spans for a trace as a flat list ordered by started_at. */
    getTraceFlat(traceId: string): Array<ObserveSpan | LLMSpan>;
    /**
     * Return the root ObserveSpan (parent_span_id IS NULL).
     * Throws if not found.
     */
    getRoot(traceId: string): ObserveSpan;
    /** Return the LLM span with the latest ended_at, or null. */
    getLastLlm(traceId: string): LLMSpan | null;
    /** Return spans matching name, optionally scoped to a trace. */
    getByName(name: string, traceId?: string): Array<ObserveSpan | LLMSpan>;
    /** Return spans of a given kind ("observe" or "llm"). */
    getByType(spanKind: string, traceId?: string): Array<ObserveSpan | LLMSpan>;
    /** Return spans with non-null error, optionally scoped to a trace. */
    getErrors(traceId?: string): Array<ObserveSpan | LLMSpan>;
    /**
     * Return lightweight trace summaries for browsing.
     *
     * Each entry contains `traceId`, `rootName`, `startedAt`, `hasError`,
     * and `observationCount`.
     */
    listTraces(limit?: number, offset?: number): Array<Record<string, unknown>>;
    /** Close the database connection. */
    close(): void;
}
//# sourceMappingURL=store.d.ts.map