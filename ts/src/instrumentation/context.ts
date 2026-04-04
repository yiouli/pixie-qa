/**
 * ObservationContext — the mutable object provided by startObservation().
 *
 * Users interact with this inside the observation callback.
 * The frozen ObserveSpan delivered to the handler is the public type.
 */

import type { Span } from "@opentelemetry/api";
import type { ObserveSpan } from "./spans";

/**
 * Extract parent span ID from an OTel span, if present.
 */
function extractParentSpanId(otelSpan: Span): string | null {
  const spanCtx = otelSpan.spanContext();
  // The OTel JS SDK doesn't expose parent directly on the Span interface.
  // We check for a `parentSpanId` property on the span object.
  const parentId = (otelSpan as unknown as Record<string, unknown>)["parentSpanId"] as
    | string
    | undefined;
  if (parentId && parentId !== "0000000000000000") {
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
export class ObservationContext {
  private readonly _otelSpan: Span;
  private readonly _input: unknown;
  private _output: unknown = null;
  private readonly _metadata: Record<string, unknown> = {};
  /** @internal */
  _error: string | null = null;

  constructor(otelSpan: Span, input: unknown) {
    this._otelSpan = otelSpan;
    this._input = input;
  }

  /** Set the output value for this observed block. */
  setOutput(value: unknown): void {
    this._output = value;
  }

  /** Accumulate a metadata key-value pair. */
  setMetadata(key: string, value: unknown): void {
    this._metadata[key] = value;
  }

  /**
   * Produce a frozen ObserveSpan from the current mutable state.
   * @internal
   */
  _snapshot(): ObserveSpan {
    const ctx = this._otelSpan.spanContext();
    const spanId = ctx.spanId;
    const traceId = ctx.traceId;
    const parentSpanId = extractParentSpanId(this._otelSpan);

    // Read timing from the span object (OTel SDK ReadableSpan exposes these)
    const readable = this._otelSpan as unknown as {
      startTime?: [number, number];
      endTime?: [number, number];
      name?: string;
    };

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

/**
 * No-op observation context used when tracing is not initialized.
 *
 * All mutator methods are silent no-ops. No OTel span is created,
 * no ObserveSpan is submitted.
 */
export class NoOpObservationContext extends ObservationContext {
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
      end: () => {},
      isRecording: () => false,
      recordException: () => {},
    } as unknown as Span;
    super(dummySpan, null);
  }

  override setOutput(_value: unknown): void {
    // silent no-op
  }

  override setMetadata(_key: string, _value: unknown): void {
    // silent no-op
  }

  /** @internal */
  override _snapshot(): ObserveSpan {
    // Return a dummy span — this should never be used
    return null as unknown as ObserveSpan;
  }
}
