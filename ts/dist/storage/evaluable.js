"use strict";
/**
 * Evaluable model and span-to-evaluable conversion.
 *
 * `Evaluable` is an immutable interface that serves as the uniform
 * data carrier for evaluators. The `UNSET` sentinel distinguishes
 * "expected output was never provided" from "expected output is
 * explicitly null/undefined".
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.UNSET = void 0;
exports.asEvaluable = asEvaluable;
// ── UNSET sentinel ───────────────────────────────────────────────────────────
/**
 * Sentinel to distinguish "not provided" from `null` / `undefined`.
 */
exports.UNSET = Symbol("UNSET");
// ── Factory / conversion ─────────────────────────────────────────────────────
function makeJsonCompatible(obj) {
    if (obj === null || obj === undefined)
        return null;
    if (typeof obj === "string" || typeof obj === "number" || typeof obj === "boolean") {
        return obj;
    }
    if (Array.isArray(obj)) {
        return obj.map(makeJsonCompatible);
    }
    if (typeof obj === "object") {
        const result = {};
        for (const [k, v] of Object.entries(obj)) {
            result[k] = makeJsonCompatible(v);
        }
        return result;
    }
    return null;
}
function observeSpanToEvaluable(span) {
    const meta = span.metadata
        ? { ...makeJsonCompatible(span.metadata) }
        : {};
    meta["trace_id"] = span.traceId;
    meta["span_id"] = span.spanId;
    return {
        evalInput: makeJsonCompatible(span.input),
        evalOutput: makeJsonCompatible(span.output),
        evalMetadata: meta,
        expectedOutput: exports.UNSET,
        evaluators: null,
        description: null,
    };
}
function llmSpanToEvaluable(span) {
    // Extract text from last output message
    let outputText = null;
    if (span.outputMessages.length > 0) {
        const last = span.outputMessages[span.outputMessages.length - 1];
        const parts = last.content
            .filter((p) => p.type === "text")
            .map((p) => p.text);
        outputText = parts.length > 0 ? parts.join("") : null;
    }
    const inputData = span.inputMessages.map((msg) => makeJsonCompatible(msg));
    const metadata = {
        trace_id: span.traceId,
        span_id: span.spanId,
        provider: span.provider,
        request_model: span.requestModel,
        response_model: span.responseModel,
        operation: span.operation,
        input_tokens: span.inputTokens,
        output_tokens: span.outputTokens,
        cache_read_tokens: span.cacheReadTokens,
        cache_creation_tokens: span.cacheCreationTokens,
        finish_reasons: [...span.finishReasons],
        error_type: span.errorType,
        tool_definitions: span.toolDefinitions.map((td) => makeJsonCompatible(td)),
    };
    return {
        evalInput: inputData,
        evalOutput: outputText,
        evalMetadata: metadata,
        expectedOutput: exports.UNSET,
        evaluators: null,
        description: null,
    };
}
/**
 * Build an `Evaluable` from a span.
 *
 * `expectedOutput` is left as `UNSET` — span data never carries
 * expected values.
 */
function asEvaluable(span) {
    if ("operation" in span) {
        return llmSpanToEvaluable(span);
    }
    return observeSpanToEvaluable(span);
}
//# sourceMappingURL=evaluable.js.map