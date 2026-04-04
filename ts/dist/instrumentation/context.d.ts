/**
 * ObservationContext — the mutable object provided by startObservation().
 *
 * Users interact with this inside the observation callback.
 * The frozen ObserveSpan delivered to the handler is the public type.
 */
import type { Span } from "@opentelemetry/api";
import type { ObserveSpan } from "./spans";
/**
 * Mutable observation context provided to startObservation() callbacks.
 *
 * Users interact with this inside the observation block via
 * `setOutput()` and `setMetadata()`. The frozen `ObserveSpan`
 * delivered to the handler is the public type.
 */
export declare class ObservationContext {
    private readonly _otelSpan;
    private readonly _input;
    private _output;
    private readonly _metadata;
    /** @internal */
    _error: string | null;
    constructor(otelSpan: Span, input: unknown);
    /** Set the output value for this observed block. */
    setOutput(value: unknown): void;
    /** Accumulate a metadata key-value pair. */
    setMetadata(key: string, value: unknown): void;
    /**
     * Produce a frozen ObserveSpan from the current mutable state.
     * @internal
     */
    _snapshot(): ObserveSpan;
}
/**
 * No-op observation context used when tracing is not initialized.
 *
 * All mutator methods are silent no-ops. No OTel span is created,
 * no ObserveSpan is submitted.
 */
export declare class NoOpObservationContext extends ObservationContext {
    constructor();
    setOutput(_value: unknown): void;
    setMetadata(_key: string, _value: unknown): void;
    /** @internal */
    _snapshot(): ObserveSpan;
}
//# sourceMappingURL=context.d.ts.map