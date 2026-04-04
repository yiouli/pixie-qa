/**
 * Main instrumentation entry points: init(), startObservation(),
 * observe(), addHandler(), removeHandler(), flush().
 *
 * Uses a callback pattern for `startObservation()` instead of Python's
 * context manager. The `observe()` function is a higher-order wrapper
 * (TypeScript method decorator pattern).
 */
import { ObservationContext } from "./context";
import { InstrumentationHandler } from "./handler";
/**
 * Reset global state. **Test-only** — not part of the public API.
 * @internal
 */
export declare function _resetState(): void;
export interface InitOptions {
    /**
     * Whether to capture message content in LLM spans.
     * @default true
     */
    captureContent?: boolean;
    /**
     * Maximum number of spans the delivery queue will buffer.
     * @default 1000
     */
    queueSize?: number;
}
/**
 * Initialize the instrumentation sub-package.
 *
 * Sets up the OpenTelemetry TracerProvider, span processor, delivery
 * queue, and activates auto-instrumentors. Idempotent — calling
 * `init()` a second time is a no-op.
 *
 * Handler registration is done separately via `addHandler()`.
 */
export declare function init(options?: InitOptions): void;
/**
 * Register a handler to receive span notifications.
 *
 * Must be called after `init()`. Multiple handlers can be registered;
 * each receives every span.
 */
export declare function addHandler(handler: InstrumentationHandler): void;
/**
 * Unregister a previously registered handler.
 *
 * Throws if the handler was not registered.
 */
export declare function removeHandler(handler: InstrumentationHandler): void;
/**
 * Options for `startObservation()`.
 */
export interface StartObservationOptions {
    /** The input value for this observation. */
    input: unknown;
    /** Optional span name. Defaults to "observe". */
    name?: string;
}
/**
 * Create an OTel span and run a callback with a mutable ObservationContext.
 *
 * If `init()` has not been called, the callback executes normally but
 * no span is captured (no-op context).
 *
 * @param options - Observation options (input, name).
 * @param callback - Function to run within the observation. Receives
 *   the `ObservationContext` for setting output/metadata.
 * @returns The return value of the callback.
 */
export declare function startObservation<T>(options: StartObservationOptions, callback: (ctx: ObservationContext) => T | Promise<T>): Promise<T>;
/**
 * Synchronous version of startObservation for non-async callbacks.
 */
export declare function startObservationSync<T>(options: StartObservationOptions, callback: (ctx: ObservationContext) => T): T;
/**
 * Higher-order function wrapper that wraps a function in a
 * `startObservation()` block.
 *
 * Automatically captures the function's arguments as input and
 * the return value as output.
 *
 * @param name - Optional span name. Defaults to `fn.name`.
 */
export declare function observe<TArgs extends unknown[], TReturn>(fn: (...args: TArgs) => Promise<TReturn>, name?: string): (...args: TArgs) => Promise<TReturn>;
export declare function observe<TArgs extends unknown[], TReturn>(fn: (...args: TArgs) => TReturn, name?: string): (...args: TArgs) => TReturn;
/**
 * Flush the delivery queue, waiting until all items are processed.
 *
 * @param timeoutSeconds - Maximum time to wait. Defaults to 5 seconds.
 * @returns `true` if all items were flushed, `false` on timeout.
 */
export declare function flush(timeoutSeconds?: number): Promise<boolean>;
//# sourceMappingURL=observation.d.ts.map