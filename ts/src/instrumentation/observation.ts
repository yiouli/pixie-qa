/**
 * Main instrumentation entry points: init(), startObservation(),
 * observe(), addHandler(), removeHandler(), flush().
 *
 * Uses a callback pattern for `startObservation()` instead of Python's
 * context manager. The `observe()` function is a higher-order wrapper
 * (TypeScript method decorator pattern).
 */

import { trace } from "@opentelemetry/api";
import type { Tracer } from "@opentelemetry/api";
import { NodeTracerProvider } from "@opentelemetry/sdk-trace-node";

import { ObservationContext, NoOpObservationContext } from "./context";
import { InstrumentationHandler, HandlerRegistry } from "./handler";
import { activateInstrumentors } from "./instrumentors";
import { LLMSpanProcessor } from "./processor";
import { DeliveryQueue } from "./queue";
import type { ObserveSpan } from "./spans";

// ── Internal state ───────────────────────────────────────────────────────────

interface State {
  registry: HandlerRegistry | null;
  deliveryQueue: DeliveryQueue | null;
  tracer: Tracer | null;
  tracerProvider: NodeTracerProvider | null;
  initialized: boolean;
}

const _state: State = {
  registry: null,
  deliveryQueue: null,
  tracer: null,
  tracerProvider: null,
  initialized: false,
};

/**
 * Reset global state. **Test-only** — not part of the public API.
 * @internal
 */
export function _resetState(): void {
  if (_state.deliveryQueue) {
    void _state.deliveryQueue.flush();
  }
  _state.registry = null;
  _state.deliveryQueue = null;
  _state.tracer = null;
  _state.tracerProvider = null;
  _state.initialized = false;
}

// ── Public API ───────────────────────────────────────────────────────────────

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
export function init(options: InitOptions = {}): void {
  if (_state.initialized) return;

  const { captureContent = true, queueSize = 1000 } = options;

  if (captureContent) {
    process.env["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] =
      "true";
  }

  const registry = new HandlerRegistry();
  const deliveryQueue = new DeliveryQueue(registry, queueSize);
  const processor = new LLMSpanProcessor(deliveryQueue);

  const provider = new NodeTracerProvider();
  provider.addSpanProcessor(processor);
  provider.register();

  _state.registry = registry;
  _state.deliveryQueue = deliveryQueue;
  _state.tracer = provider.getTracer("pixie.instrumentation");
  _state.tracerProvider = provider;
  _state.initialized = true;

  activateInstrumentors();
}

/**
 * Register a handler to receive span notifications.
 *
 * Must be called after `init()`. Multiple handlers can be registered;
 * each receives every span.
 */
export function addHandler(handler: InstrumentationHandler): void {
  if (!_state.registry) {
    throw new Error(
      "pixie.instrumentation.init() must be called before addHandler()"
    );
  }
  _state.registry.add(handler);
}

/**
 * Unregister a previously registered handler.
 *
 * Throws if the handler was not registered.
 */
export function removeHandler(handler: InstrumentationHandler): void {
  if (!_state.registry) {
    throw new Error(
      "pixie.instrumentation.init() must be called before removeHandler()"
    );
  }
  _state.registry.remove(handler);
}

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
export async function startObservation<T>(
  options: StartObservationOptions,
  callback: (ctx: ObservationContext) => T | Promise<T>
): Promise<T> {
  if (!_state.tracer) {
    const noOp = new NoOpObservationContext();
    return callback(noOp);
  }

  const tracer = _state.tracer;
  const spanName = options.name ?? "observe";

  return tracer.startActiveSpan(spanName, async (otelSpan) => {
    const ctx = new ObservationContext(otelSpan, options.input);
    try {
      const result = await callback(ctx);
      return result;
    } catch (err: unknown) {
      ctx._error =
        err instanceof Error ? err.constructor.name : String(err);
      throw err;
    } finally {
      otelSpan.end();
      const observeSpan = ctx._snapshot();
      if (observeSpan && _state.deliveryQueue) {
        _state.deliveryQueue.submit(observeSpan);
      }
    }
  });
}

/**
 * Synchronous version of startObservation for non-async callbacks.
 */
export function startObservationSync<T>(
  options: StartObservationOptions,
  callback: (ctx: ObservationContext) => T
): T {
  if (!_state.tracer) {
    const noOp = new NoOpObservationContext();
    return callback(noOp);
  }

  const tracer = _state.tracer;
  const spanName = options.name ?? "observe";

  return tracer.startActiveSpan(spanName, (otelSpan) => {
    const ctx = new ObservationContext(otelSpan, options.input);
    try {
      const result = callback(ctx);
      return result;
    } catch (err: unknown) {
      ctx._error =
        err instanceof Error ? err.constructor.name : String(err);
      throw err;
    } finally {
      otelSpan.end();
      const observeSpan = ctx._snapshot();
      if (observeSpan && _state.deliveryQueue) {
        _state.deliveryQueue.submit(observeSpan);
      }
    }
  });
}

/**
 * Higher-order function wrapper that wraps a function in a
 * `startObservation()` block.
 *
 * Automatically captures the function's arguments as input and
 * the return value as output.
 *
 * @param name - Optional span name. Defaults to `fn.name`.
 */
export function observe<TArgs extends unknown[], TReturn>(
  fn: (...args: TArgs) => Promise<TReturn>,
  name?: string
): (...args: TArgs) => Promise<TReturn>;
export function observe<TArgs extends unknown[], TReturn>(
  fn: (...args: TArgs) => TReturn,
  name?: string
): (...args: TArgs) => TReturn;
export function observe<TArgs extends unknown[], TReturn>(
  fn: (...args: TArgs) => TReturn | Promise<TReturn>,
  name?: string
): (...args: TArgs) => TReturn | Promise<TReturn> {
  const spanName = name ?? fn.name ?? "observe";

  const wrapper = (...args: TArgs): TReturn | Promise<TReturn> => {
    const serializedInput = args;

    if (!_state.tracer) {
      return fn(...args);
    }

    // Check if the function returns a promise (async function)
    const result = startObservation<TReturn>(
      { input: serializedInput, name: spanName },
      async (ctx) => {
        const ret = await fn(...args);
        ctx.setOutput(ret);
        return ret;
      }
    );
    return result;
  };

  // Preserve function name for debugging
  Object.defineProperty(wrapper, "name", { value: spanName });
  return wrapper;
}

/**
 * Flush the delivery queue, waiting until all items are processed.
 *
 * @param timeoutSeconds - Maximum time to wait. Defaults to 5 seconds.
 * @returns `true` if all items were flushed, `false` on timeout.
 */
export async function flush(timeoutSeconds = 5.0): Promise<boolean> {
  if (_state.deliveryQueue) {
    return _state.deliveryQueue.flush(timeoutSeconds);
  }
  return true;
}
