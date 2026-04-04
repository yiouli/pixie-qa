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
export class DeliveryQueue {
  private readonly _handler: InstrumentationHandler;
  private readonly _maxSize: number;
  private readonly _queue: SpanItem[] = [];
  private _droppedCount = 0;
  private _processing = false;
  private _flushResolvers: Array<() => void> = [];

  constructor(handler: InstrumentationHandler, maxSize = 1000) {
    this._handler = handler;
    this._maxSize = maxSize;
  }

  /**
   * Submit a span for delivery. Drops silently on full queue.
   */
  submit(item: SpanItem): void {
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
  async flush(timeoutSeconds = 5.0): Promise<boolean> {
    if (this._queue.length === 0 && !this._processing) {
      return true;
    }

    return new Promise<boolean>((resolve) => {
      const timer = setTimeout(() => {
        const idx = this._flushResolvers.indexOf(doResolve);
        if (idx !== -1) this._flushResolvers.splice(idx, 1);
        resolve(false);
      }, timeoutSeconds * 1000);

      const doResolve = (): void => {
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
  get droppedCount(): number {
    return this._droppedCount;
  }

  private _processQueue(): void {
    if (this._processing) return;
    this._processing = true;

    void this._processLoop();
  }

  private async _processLoop(): Promise<void> {
    while (this._queue.length > 0) {
      const item = this._queue.shift()!;
      await this._dispatch(item);
    }
    this._processing = false;
    this._resolveFlushers();
  }

  private async _dispatch(item: SpanItem): Promise<void> {
    try {
      if ("operation" in item) {
        await this._handler.onLlm(item as LLMSpan);
      } else {
        await this._handler.onObserve(item as ObserveSpan);
      }
    } catch {
      // Handler exceptions are silently swallowed
    }
  }

  private _resolveFlushers(): void {
    const resolvers = [...this._flushResolvers];
    this._flushResolvers = [];
    for (const resolve of resolvers) {
      resolve();
    }
  }
}
