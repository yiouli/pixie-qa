"use strict";
/**
 * DeliveryQueue — async queue for delivering spans to handlers.
 *
 * Uses Node.js Promise-based async patterns instead of Python's
 * threading + asyncio approach. Items are processed sequentially
 * from the queue to maintain ordering guarantees.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.DeliveryQueue = void 0;
/**
 * Async delivery queue for span processing.
 *
 * Spans are enqueued via `submit()` and processed asynchronously by
 * a background consumer. The queue has a maximum size; items submitted
 * when the queue is full are silently dropped.
 */
class DeliveryQueue {
    _handler;
    _maxSize;
    _queue = [];
    _droppedCount = 0;
    _processing = false;
    _flushResolvers = [];
    constructor(handler, maxSize = 1000) {
        this._handler = handler;
        this._maxSize = maxSize;
    }
    /**
     * Submit a span for delivery. Drops silently on full queue.
     */
    submit(item) {
        if (this._queue.length >= this._maxSize) {
            this._droppedCount++;
            return;
        }
        this._queue.push(item);
        this._processQueue();
    }
    /**
     * Wait until all queued items and their async handlers are done.
     */
    async flush(timeoutSeconds = 5.0) {
        if (this._queue.length === 0 && !this._processing) {
            return true;
        }
        return new Promise((resolve) => {
            const timer = setTimeout(() => {
                const idx = this._flushResolvers.indexOf(doResolve);
                if (idx !== -1)
                    this._flushResolvers.splice(idx, 1);
                resolve(false);
            }, timeoutSeconds * 1000);
            const doResolve = () => {
                clearTimeout(timer);
                resolve(true);
            };
            this._flushResolvers.push(doResolve);
            // If not currently processing, check if already empty
            if (this._queue.length === 0 && !this._processing) {
                this._resolveFlushers();
            }
        });
    }
    /**
     * Number of spans dropped due to full queue.
     */
    get droppedCount() {
        return this._droppedCount;
    }
    _processQueue() {
        if (this._processing)
            return;
        this._processing = true;
        void this._processLoop();
    }
    async _processLoop() {
        while (this._queue.length > 0) {
            const item = this._queue.shift();
            await this._dispatch(item);
        }
        this._processing = false;
        this._resolveFlushers();
    }
    async _dispatch(item) {
        try {
            if ("operation" in item) {
                await this._handler.onLlm(item);
            }
            else {
                await this._handler.onObserve(item);
            }
        }
        catch {
            // Handler exceptions are silently swallowed
        }
    }
    _resolveFlushers() {
        const resolvers = [...this._flushResolvers];
        this._flushResolvers = [];
        for (const resolve of resolvers) {
            resolve();
        }
    }
}
exports.DeliveryQueue = DeliveryQueue;
//# sourceMappingURL=queue.js.map