/**
 * DeliveryQueue — async queue for delivering spans to handlers.
 *
 * Uses Node.js Promise-based async patterns instead of Python's
 * threading + asyncio approach. Items are processed sequentially
 * from the queue to maintain ordering guarantees.
 */
import type { InstrumentationHandler } from "./handler";
import type { LLMSpan, ObserveSpan } from "./spans";
type SpanItem = LLMSpan | ObserveSpan;
/**
 * Async delivery queue for span processing.
 *
 * Spans are enqueued via `submit()` and processed asynchronously by
 * a background consumer. The queue has a maximum size; items submitted
 * when the queue is full are silently dropped.
 */
export declare class DeliveryQueue {
    private readonly _handler;
    private readonly _maxSize;
    private readonly _queue;
    private _droppedCount;
    private _processing;
    private _flushResolvers;
    constructor(handler: InstrumentationHandler, maxSize?: number);
    /**
     * Submit a span for delivery. Drops silently on full queue.
     */
    submit(item: SpanItem): void;
    /**
     * Wait until all queued items and their async handlers are done.
     */
    flush(timeoutSeconds?: number): Promise<boolean>;
    /**
     * Number of spans dropped due to full queue.
     */
    get droppedCount(): number;
    private _processQueue;
    private _processLoop;
    private _dispatch;
    private _resolveFlushers;
}
export {};
//# sourceMappingURL=queue.d.ts.map