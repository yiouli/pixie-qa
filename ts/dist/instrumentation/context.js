"use strict";
/**
 * ObservationContext — the mutable object provided by startObservation().
 *
 * Users interact with this inside the observation callback.
 * The frozen ObserveSpan delivered to the handler is the public type.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.NoOpObservationContext = exports.ObservationContext = void 0;
const NULL_SPAN_ID = "0000000000000000";
/**
 * Extract parent span ID from an OTel span, if present.
 */
function extractParentSpanId(otelSpan) {
    const spanCtx = otelSpan.spanContext();
    // The OTel JS SDK doesn't expose parent directly on the Span interface.
    // We check for a `parentSpanId` property on the span object.
    const parentId = otelSpan["parentSpanId"];
    if (parentId && parentId !== NULL_SPAN_ID) {
        return parentId;
    }
    return null;
}
/**
 * Mutable observation context provided to startObservation() callbacks.
 *
 * Users interact with this inside the observation block via
 * `setOutput()` and `setMetadata()`. The frozen `ObserveSpan`
 * delivered to the handler is the public type.
 */
class ObservationContext {
    _otelSpan;
    _input;
    _output = null;
    _metadata = {};
    /** @internal */
    _error = null;
    constructor(otelSpan, input) {
        this._otelSpan = otelSpan;
        this._input = input;
    }
    /** Set the output value for this observed block. */
    setOutput(value) {
        this._output = value;
    }
    /** Accumulate a metadata key-value pair. */
    setMetadata(key, value) {
        this._metadata[key] = value;
    }
    /**
     * Produce a frozen ObserveSpan from the current mutable state.
     * @internal
     */
    _snapshot() {
        const ctx = this._otelSpan.spanContext();
        const spanId = ctx.spanId;
        const traceId = ctx.traceId;
        const parentSpanId = extractParentSpanId(this._otelSpan);
        // Read timing from the span object (OTel SDK ReadableSpan exposes these)
        const readable = this._otelSpan;
        const startHrTime = readable.startTime ?? [0, 0];
        const endHrTime = readable.endTime ?? [
            Math.floor(Date.now() / 1000),
            (Date.now() % 1000) * 1e6,
        ];
        const startMs = startHrTime[0] * 1000 + startHrTime[1] / 1e6;
        const endMs = endHrTime[0] * 1000 + endHrTime[1] / 1e6;
        return {
            spanId,
            traceId,
            parentSpanId,
            startedAt: new Date(startMs),
            endedAt: new Date(endMs),
            durationMs: endMs - startMs,
            name: readable.name ?? null,
            input: this._input,
            output: this._output,
            metadata: { ...this._metadata },
            error: this._error,
        };
    }
}
exports.ObservationContext = ObservationContext;
/**
 * No-op observation context used when tracing is not initialized.
 *
 * All mutator methods are silent no-ops. No OTel span is created,
 * no ObserveSpan is submitted.
 */
class NoOpObservationContext extends ObservationContext {
    constructor() {
        // Use a dummy span-like object that satisfies the Span interface minimally
        const dummySpan = {
            spanContext: () => ({
                traceId: "00000000000000000000000000000000",
                spanId: "0000000000000000",
                traceFlags: 0,
            }),
            setAttribute: () => dummySpan,
            setAttributes: () => dummySpan,
            addEvent: () => dummySpan,
            addLink: () => dummySpan,
            setStatus: () => dummySpan,
            updateName: () => dummySpan,
            end: () => { },
            isRecording: () => false,
            recordException: () => { },
        };
        super(dummySpan, null);
    }
    setOutput(_value) {
        // silent no-op
    }
    setMetadata(_key, _value) {
        // silent no-op
    }
    /** @internal */
    _snapshot() {
        // NoOp context should never produce a span — throw if called unexpectedly
        throw new Error("NoOpObservationContext._snapshot() should never be called");
    }
}
exports.NoOpObservationContext = NoOpObservationContext;
//# sourceMappingURL=context.js.map