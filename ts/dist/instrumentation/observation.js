"use strict";
/**
 * Main instrumentation entry points: init(), startObservation(),
 * observe(), addHandler(), removeHandler(), flush().
 *
 * Uses a callback pattern for `startObservation()` instead of Python's
 * context manager. The `observe()` function is a higher-order wrapper
 * (TypeScript method decorator pattern).
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports._resetState = _resetState;
exports.init = init;
exports.addHandler = addHandler;
exports.removeHandler = removeHandler;
exports.startObservation = startObservation;
exports.startObservationSync = startObservationSync;
exports.observe = observe;
exports.flush = flush;
const sdk_trace_node_1 = require("@opentelemetry/sdk-trace-node");
const context_1 = require("./context");
const handler_1 = require("./handler");
const instrumentors_1 = require("./instrumentors");
const processor_1 = require("./processor");
const queue_1 = require("./queue");
const _state = {
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
function _resetState() {
    if (_state.deliveryQueue) {
        void _state.deliveryQueue.flush();
    }
    _state.registry = null;
    _state.deliveryQueue = null;
    _state.tracer = null;
    _state.tracerProvider = null;
    _state.initialized = false;
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
function init(options = {}) {
    if (_state.initialized)
        return;
    const { captureContent = true, queueSize = 1000 } = options;
    if (captureContent) {
        process.env["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] =
            "true";
    }
    const registry = new handler_1.HandlerRegistry();
    const deliveryQueue = new queue_1.DeliveryQueue(registry, queueSize);
    const processor = new processor_1.LLMSpanProcessor(deliveryQueue);
    const provider = new sdk_trace_node_1.NodeTracerProvider();
    provider.addSpanProcessor(processor);
    provider.register();
    _state.registry = registry;
    _state.deliveryQueue = deliveryQueue;
    _state.tracer = provider.getTracer("pixie.instrumentation");
    _state.tracerProvider = provider;
    _state.initialized = true;
    (0, instrumentors_1.activateInstrumentors)();
}
/**
 * Register a handler to receive span notifications.
 *
 * Must be called after `init()`. Multiple handlers can be registered;
 * each receives every span.
 */
function addHandler(handler) {
    if (!_state.registry) {
        throw new Error("pixie.instrumentation.init() must be called before addHandler()");
    }
    _state.registry.add(handler);
}
/**
 * Unregister a previously registered handler.
 *
 * Throws if the handler was not registered.
 */
function removeHandler(handler) {
    if (!_state.registry) {
        throw new Error("pixie.instrumentation.init() must be called before removeHandler()");
    }
    _state.registry.remove(handler);
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
async function startObservation(options, callback) {
    if (!_state.tracer) {
        const noOp = new context_1.NoOpObservationContext();
        return callback(noOp);
    }
    const tracer = _state.tracer;
    const spanName = options.name ?? "observe";
    return tracer.startActiveSpan(spanName, async (otelSpan) => {
        const ctx = new context_1.ObservationContext(otelSpan, options.input);
        try {
            const result = await callback(ctx);
            return result;
        }
        catch (err) {
            ctx._error =
                err instanceof Error ? err.constructor.name : String(err);
            throw err;
        }
        finally {
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
function startObservationSync(options, callback) {
    if (!_state.tracer) {
        const noOp = new context_1.NoOpObservationContext();
        return callback(noOp);
    }
    const tracer = _state.tracer;
    const spanName = options.name ?? "observe";
    return tracer.startActiveSpan(spanName, (otelSpan) => {
        const ctx = new context_1.ObservationContext(otelSpan, options.input);
        try {
            const result = callback(ctx);
            return result;
        }
        catch (err) {
            ctx._error =
                err instanceof Error ? err.constructor.name : String(err);
            throw err;
        }
        finally {
            otelSpan.end();
            const observeSpan = ctx._snapshot();
            if (observeSpan && _state.deliveryQueue) {
                _state.deliveryQueue.submit(observeSpan);
            }
        }
    });
}
function observe(fn, name) {
    const spanName = name ?? fn.name ?? "observe";
    const wrapper = (...args) => {
        const serializedInput = args;
        if (!_state.tracer) {
            return fn(...args);
        }
        // Check if the function returns a promise (async function)
        const result = startObservation({ input: serializedInput, name: spanName }, async (ctx) => {
            const ret = await fn(...args);
            ctx.setOutput(ret);
            return ret;
        });
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
async function flush(timeoutSeconds = 5.0) {
    if (_state.deliveryQueue) {
        return _state.deliveryQueue.flush(timeoutSeconds);
    }
    return true;
}
//# sourceMappingURL=observation.js.map