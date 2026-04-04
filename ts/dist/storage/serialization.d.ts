/**
 * Span serialization and deserialization for database storage.
 *
 * Handles conversion between readonly span interfaces and plain objects
 * suitable for SQLite table rows, including nested types and Date↔ISO
 * string conversion.
 */
import type { LLMSpan, MessageContent, ObserveSpan } from "../instrumentation/spans";
/**
 * Convert a span to a dict matching the Observation table columns.
 */
export declare function serializeSpan(span: ObserveSpan | LLMSpan): Record<string, unknown>;
/**
 * Reconstruct a span from a table row dict.
 */
export declare function deserializeSpan(row: Record<string, unknown>): ObserveSpan | LLMSpan;
export type { MessageContent };
//# sourceMappingURL=serialization.d.ts.map