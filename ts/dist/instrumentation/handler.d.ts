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
export declare abstract class InstrumentationHandler {
    /**
     * Called when an LLM provider call completes.
     * Default: no-op. Override to capture LLM call data.
     * Exceptions are caught and suppressed.
     */
    onLlm(_span: LLMSpan): Promise<void>;
    /**
     * Called when a startObservation() block completes.
     * Default: no-op. Override to capture eval-relevant data.
     * Exceptions are caught and suppressed.
     */
    onObserve(_span: ObserveSpan): Promise<void>;
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
export declare class HandlerRegistry extends InstrumentationHandler {
    private _handlers;
    add(handler: InstrumentationHandler): void;
    remove(handler: InstrumentationHandler): void;
    onLlm(span: LLMSpan): Promise<void>;
    onObserve(span: ObserveSpan): Promise<void>;
}
//# sourceMappingURL=handler.d.ts.map