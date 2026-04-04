/**
 * In-memory trace capture for eval test execution.
 *
 * Provides `MemoryTraceHandler` that collects spans into a list, and
 * `captureTraces()` — a callback-based wrapper (replacing Python's
 * context manager) for scoped trace capture during tests.
 */
import { InstrumentationHandler } from "../instrumentation";
import type { LLMSpan, ObserveSpan } from "../instrumentation/spans";
import { ObservationNode } from "../storage/tree";
/**
 * Collects ObserveSpan and LLMSpan instances into an in-memory list.
 *
 * Used by the eval test runner to capture traces without writing to disk.
 */
export declare class MemoryTraceHandler extends InstrumentationHandler {
    spans: Array<ObserveSpan | LLMSpan>;
    onLlm(span: LLMSpan): Promise<void>;
    onObserve(span: ObserveSpan): Promise<void>;
    /** Filter spans by traceId and build the tree. */
    getTrace(traceId: string): ObservationNode[];
    /** Group all captured spans by traceId and build trees. */
    getAllTraces(): Map<string, ObservationNode[]>;
    /** Remove all collected spans. */
    clear(): void;
}
/**
 * Capture traces during callback execution.
 *
 * Replaces Python's `capture_traces()` context manager with a callback
 * pattern. Installs a MemoryTraceHandler, runs the callback, flushes
 * the delivery queue, then removes the handler.
 *
 * @returns The handler with all captured spans.
 */
export declare function captureTraces<T>(callback: (handler: MemoryTraceHandler) => T | Promise<T>): Promise<{
    result: T;
    handler: MemoryTraceHandler;
}>;
//# sourceMappingURL=traceCapture.d.ts.map