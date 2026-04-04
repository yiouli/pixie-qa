"use strict";
/**
 * LLMSpanProcessor — converts OpenInference span attributes to typed LLMSpan objects.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.LLMSpanProcessor = void 0;
const api_1 = require("@opentelemetry/api");
const spans_1 = require("./spans");
// ── Helper functions ─────────────────────────────────────────────────────────
function inferProvider(modelName) {
    const lower = modelName.toLowerCase();
    if (lower.includes("gpt") || lower.includes("o1") || lower.includes("o3")) {
        return "openai";
    }
    if (lower.includes("claude"))
        return "anthropic";
    if (lower.includes("gemini"))
        return "google";
    if (lower.includes("command") || lower.includes("coral"))
        return "cohere";
    if (lower.includes("llama") ||
        lower.includes("mixtral") ||
        lower.includes("mistral")) {
        return "meta";
    }
    return "unknown";
}
function parseJson(raw) {
    try {
        const result = JSON.parse(raw);
        if (typeof result === "object" && result !== null && !Array.isArray(result)) {
            return result;
        }
        return {};
    }
    catch {
        return {};
    }
}
function toFloatOrNull(value) {
    if (value === null || value === undefined)
        return null;
    const n = Number(value);
    return Number.isNaN(n) ? null : n;
}
function toIntOrNull(value) {
    if (value === null || value === undefined)
        return null;
    const n = parseInt(String(value), 10);
    return Number.isNaN(n) ? null : n;
}
function parseContentParts(attrs, prefix) {
    const parts = [];
    let j = 0;
    while (true) {
        const typeKey = `${prefix}.contents.${j}.message_content.type`;
        const contentType = attrs[typeKey];
        if (contentType === undefined || contentType === null)
            break;
        if (contentType === "text") {
            const textKey = `${prefix}.contents.${j}.message_content.text`;
            const text = String(attrs[textKey] ?? "");
            parts.push((0, spans_1.createTextContent)(text));
        }
        else if (contentType === "image") {
            const urlKey = `${prefix}.contents.${j}.message_content.image.url.url`;
            const detailKey = `${prefix}.contents.${j}.message_content.image.url.detail`;
            const url = String(attrs[urlKey] ?? "");
            const detailRaw = attrs[detailKey];
            const detail = detailRaw != null ? String(detailRaw) : null;
            parts.push((0, spans_1.createImageContent)(url, detail));
        }
        j++;
    }
    if (parts.length === 0) {
        const contentKey = `${prefix}.content`;
        const contentRaw = attrs[contentKey];
        if (contentRaw != null) {
            parts.push((0, spans_1.createTextContent)(String(contentRaw)));
        }
    }
    return parts;
}
function parseToolCalls(attrs, prefix) {
    const toolCalls = [];
    let j = 0;
    while (true) {
        const nameKey = `${prefix}.tool_calls.${j}.tool_call.function.name`;
        const name = attrs[nameKey];
        if (name === undefined || name === null)
            break;
        const argsKey = `${prefix}.tool_calls.${j}.tool_call.function.arguments`;
        const argsRaw = attrs[argsKey];
        let args;
        if (typeof argsRaw === "string") {
            try {
                args = JSON.parse(argsRaw);
            }
            catch {
                args = { _raw: argsRaw };
            }
        }
        else if (typeof argsRaw === "object" && argsRaw !== null) {
            args = argsRaw;
        }
        else {
            args = {};
        }
        const idKey = `${prefix}.tool_calls.${j}.tool_call.id`;
        const callIdRaw = attrs[idKey];
        const callId = callIdRaw != null ? String(callIdRaw) : null;
        toolCalls.push({ name: String(name), arguments: args, id: callId });
        j++;
    }
    return toolCalls;
}
function parseInputMessages(attrs) {
    const messages = [];
    let i = 0;
    while (true) {
        const prefix = `llm.input_messages.${i}.message`;
        const roleKey = `${prefix}.role`;
        const role = attrs[roleKey];
        if (role === undefined || role === null)
            break;
        const roleStr = String(role).toLowerCase();
        if (roleStr === "system") {
            const contentKey = `${prefix}.content`;
            const content = String(attrs[contentKey] ?? "");
            messages.push((0, spans_1.createSystemMessage)(content));
        }
        else if (roleStr === "user") {
            const parts = parseContentParts(attrs, prefix);
            messages.push((0, spans_1.createUserMessage)(parts));
        }
        else if (roleStr === "assistant") {
            const parts = parseContentParts(attrs, prefix);
            const toolCalls = parseToolCalls(attrs, prefix);
            messages.push((0, spans_1.createAssistantMessage)({ content: parts, toolCalls }));
        }
        else if (roleStr === "tool") {
            const contentKey = `${prefix}.content`;
            const content = String(attrs[contentKey] ?? "");
            const toolCallIdRaw = attrs[`${prefix}.tool_call_id`];
            const toolCallId = toolCallIdRaw != null ? String(toolCallIdRaw) : null;
            const toolNameRaw = attrs[`${prefix}.name`];
            const toolName = toolNameRaw != null ? String(toolNameRaw) : null;
            messages.push((0, spans_1.createToolResultMessage)({ content, toolCallId, toolName }));
        }
        i++;
    }
    return messages;
}
function parseOutputMessages(attrs) {
    const messages = [];
    let i = 0;
    while (true) {
        const prefix = `llm.output_messages.${i}.message`;
        const roleKey = `${prefix}.role`;
        const role = attrs[roleKey];
        if (role === undefined || role === null)
            break;
        const parts = parseContentParts(attrs, prefix);
        const toolCalls = parseToolCalls(attrs, prefix);
        const finishReasonRaw = attrs[`${prefix}.finish_reason`];
        const finishReason = finishReasonRaw != null ? String(finishReasonRaw) : null;
        messages.push((0, spans_1.createAssistantMessage)({ content: parts, toolCalls, finishReason }));
        i++;
    }
    return messages;
}
function parseToolDefinitions(attrs) {
    const tools = [];
    let i = 0;
    while (true) {
        const nameKey = `llm.tools.${i}.tool.name`;
        const name = attrs[nameKey];
        if (name === undefined || name === null)
            break;
        const descRaw = attrs[`llm.tools.${i}.tool.description`];
        const description = descRaw != null ? String(descRaw) : null;
        const schemaRaw = attrs[`llm.tools.${i}.tool.json_schema`];
        let parameters = null;
        if (typeof schemaRaw === "string") {
            const parsed = parseJson(schemaRaw);
            parameters = Object.keys(parsed).length > 0 ? parsed : null;
        }
        else if (typeof schemaRaw === "object" && schemaRaw !== null) {
            parameters = schemaRaw;
        }
        tools.push({ name: String(name), description, parameters });
        i++;
    }
    return tools;
}
const NULL_SPAN_ID = "0000000000000000";
// ── Processor ────────────────────────────────────────────────────────────────
/**
 * OTel SpanProcessor that converts OpenInference LLM spans to typed
 * LLMSpan objects and submits them to the delivery queue.
 */
class LLMSpanProcessor {
    _deliveryQueue;
    constructor(deliveryQueue) {
        this._deliveryQueue = deliveryQueue;
    }
    onStart(_span, _parentContext) {
        // No-op — we only process completed spans.
    }
    onEnd(span) {
        try {
            const attrs = span.attributes
                ? { ...span.attributes }
                : {};
            const spanKind = attrs["openinference.span.kind"];
            if (spanKind !== "LLM" && spanKind !== "EMBEDDING") {
                return;
            }
            const llmSpan = this._buildLlmSpan(span, attrs, String(spanKind));
            this._deliveryQueue.submit(llmSpan);
        }
        catch {
            // Never raise from onEnd
        }
    }
    shutdown() {
        return Promise.resolve();
    }
    forceFlush() {
        return this._deliveryQueue.flush().then(() => undefined);
    }
    _buildLlmSpan(span, attrs, spanKind) {
        // Identity / timing
        const ctx = span.spanContext();
        const spanId = ctx.spanId;
        const traceId = ctx.traceId;
        const parentSpanId = span.parentSpanId && span.parentSpanId !== NULL_SPAN_ID
            ? span.parentSpanId
            : null;
        const startHr = span.startTime;
        const endHr = span.endTime;
        const startMs = startHr[0] * 1000 + startHr[1] / 1e6;
        const endMs = endHr[0] * 1000 + endHr[1] / 1e6;
        const startedAt = new Date(startMs);
        const endedAt = new Date(endMs);
        const durationMs = endMs - startMs;
        // Provider / model
        const requestModel = String(attrs["llm.model_name"] ?? attrs["gen_ai.request.model"] ?? "");
        const responseModelRaw = attrs["gen_ai.response.model"];
        const responseModel = responseModelRaw != null ? String(responseModelRaw) : null;
        const provider = String(attrs["gen_ai.system"] ?? "") || inferProvider(requestModel);
        const operation = spanKind === "EMBEDDING" ? "embedding" : "chat";
        // Token usage
        const inputTokens = Number(attrs["llm.token_count.prompt"] ?? 0);
        const outputTokens = Number(attrs["llm.token_count.completion"] ?? 0);
        const cacheReadTokens = Number(attrs["llm.token_count.cache_read"] ?? 0);
        const cacheCreationTokens = Number(attrs["llm.token_count.cache_creation"] ?? 0);
        // Request parameters
        const params = parseJson(String(attrs["llm.invocation_parameters"] ?? "{}"));
        const requestTemperature = toFloatOrNull(params["temperature"]);
        const requestMaxTokens = toIntOrNull(params["max_tokens"] ?? params["max_completion_tokens"]);
        const requestTopP = toFloatOrNull(params["top_p"]);
        // Response / error
        const responseIdRaw = attrs["llm.response_id"] ?? attrs["gen_ai.response.id"];
        const responseId = responseIdRaw != null ? String(responseIdRaw) : null;
        const outputTypeRaw = attrs["gen_ai.output.type"];
        const outputType = outputTypeRaw != null ? String(outputTypeRaw) : null;
        const errorTypeRaw = attrs["error.type"];
        let errorType = null;
        if (errorTypeRaw != null) {
            errorType = String(errorTypeRaw);
        }
        else if (span.status &&
            span.status.code === api_1.SpanStatusCode.ERROR) {
            errorType = "error";
        }
        // Messages
        const inputMessages = parseInputMessages(attrs);
        const outputMessages = parseOutputMessages(attrs);
        const finishReasons = outputMessages
            .map((m) => m.finishReason)
            .filter((r) => r !== null);
        // Tool definitions
        const toolDefinitions = parseToolDefinitions(attrs);
        return {
            spanId,
            traceId,
            parentSpanId,
            startedAt,
            endedAt,
            durationMs,
            operation,
            provider,
            requestModel,
            responseModel,
            inputTokens,
            outputTokens,
            cacheReadTokens,
            cacheCreationTokens,
            requestTemperature,
            requestMaxTokens,
            requestTopP,
            finishReasons,
            responseId,
            outputType,
            errorType,
            inputMessages,
            outputMessages,
            toolDefinitions,
        };
    }
}
exports.LLMSpanProcessor = LLMSpanProcessor;
//# sourceMappingURL=processor.js.map