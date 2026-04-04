/**
 * InstrumentationHandler base class and handler registry.
 */

import type { LLMSpan, ObserveSpan } from "./spans";

/**
 * Base class for instrumentation handlers.
 *
 * Both methods are optional async overrides — a handler only implementing
 * `onLlm` is valid, and vice versa. Implementations may be long-running
 * (e.g. calling external APIs) since each handler runs concurrently with
 * other registered handlers.
 */
export abstract class InstrumentationHandler {
  /**
   * Called when an LLM provider call completes.
   * Default: no-op. Override to capture LLM call data.
   * Exceptions are caught and suppressed.
   */
  async onLlm(_span: LLMSpan): Promise<void> {
    // no-op
  }

  /**
   * Called when a startObservation() block completes.
   * Default: no-op. Override to capture eval-relevant data.
   * Exceptions are caught and suppressed.
   */
  async onObserve(_span: ObserveSpan): Promise<void> {
    // no-op
  }
}

/**
 * Fan-out handler that dispatches to multiple registered handlers.
 *
 * Each handler runs concurrently via `Promise.allSettled`; per-handler
 * exceptions are isolated so one failing handler does not prevent
 * delivery to the remaining handlers.
 *
 * @internal
 */
export class HandlerRegistry extends InstrumentationHandler {
  private _handlers: InstrumentationHandler[] = [];

  add(handler: InstrumentationHandler): void {
    this._handlers.push(handler);
  }

  remove(handler: InstrumentationHandler): void {
    const idx = this._handlers.indexOf(handler);
    if (idx === -1) {
      throw new Error("Handler not found in registry");
    }
    this._handlers.splice(idx, 1);
  }

  async onLlm(span: LLMSpan): Promise<void> {
    const snapshot = [...this._handlers];
    await Promise.allSettled(snapshot.map((h) => h.onLlm(span)));
  }

  async onObserve(span: ObserveSpan): Promise<void> {
    const snapshot = [...this._handlers];
    await Promise.allSettled(snapshot.map((h) => h.onObserve(span)));
  }
}
