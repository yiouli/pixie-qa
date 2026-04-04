/**
 * LLMSpanProcessor — converts OpenInference span attributes to typed LLMSpan objects.
 */
import type { Context } from "@opentelemetry/api";
import type { ReadableSpan, SpanProcessor } from "@opentelemetry/sdk-trace-base";
import type { DeliveryQueue } from "./queue";
/**
 * OTel SpanProcessor that converts OpenInference LLM spans to typed
 * LLMSpan objects and submits them to the delivery queue.
 */
export declare class LLMSpanProcessor implements SpanProcessor {
    private readonly _deliveryQueue;
    constructor(deliveryQueue: DeliveryQueue);
    onStart(_span: ReadableSpan, _parentContext?: Context): void;
    onEnd(span: ReadableSpan): void;
    shutdown(): Promise<void>;
    forceFlush(): Promise<void>;
    private _buildLlmSpan;
}
//# sourceMappingURL=processor.d.ts.map