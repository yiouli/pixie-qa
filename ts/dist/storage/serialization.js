"use strict";
/**
 * Span serialization and deserialization for database storage.
 *
 * Handles conversion between readonly span interfaces and plain objects
 * suitable for SQLite table rows, including nested types and Date↔ISO
 * string conversion.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.serializeSpan = serializeSpan;
exports.deserializeSpan = deserializeSpan;
// ── Serialize ────────────────────────────────────────────────────────────────
/**
 * Convert a span to a dict matching the Observation table columns.
 */
function serializeSpan(span) {
    const data = toPlainObject(span);
    if ("operation" in span) {
        // LLMSpan
        return {
            id: span.spanId,
            trace_id: span.traceId,
            parent_span_id: span.parentSpanId,
            span_kind: "llm",
            name: span.requestModel,
            data,
            error: span.errorType,
            started_at: span.startedAt.toISOString(),
            ended_at: span.endedAt.toISOString(),
            duration_ms: span.durationMs,
        };
    }
    // ObserveSpan
    return {
        id: span.spanId,
        trace_id: span.traceId,
        parent_span_id: span.parentSpanId,
        span_kind: "observe",
        name: span.name,
        data,
        error: span.error,
        started_at: span.startedAt.toISOString(),
        ended_at: span.endedAt.toISOString(),
        duration_ms: span.durationMs,
    };
}
/**
 * Recursively convert an object to a JSON-safe plain object.
 *
 * - `Date` → ISO 8601 string
 * - `readonly` arrays → plain arrays
 * - Other primitives pass through unchanged.
 */
function toPlainObject(obj) {
    if (obj === null || obj === undefined)
        return null;
    if (obj instanceof Date)
        return obj.toISOString();
    if (typeof obj === "string" || typeof obj === "number" || typeof obj === "boolean") {
        return obj;
    }
    if (Array.isArray(obj)) {
        return obj.map(toPlainObject);
    }
    if (typeof obj === "object") {
        const result = {};
        for (const [k, v] of Object.entries(obj)) {
            result[k] = toPlainObject(v);
        }
        return result;
    }
    return obj;
}
// ── Deserialize ──────────────────────────────────────────────────────────────
/**
 * Reconstruct a span from a table row dict.
 */
function deserializeSpan(row) {
    const kind = row["span_kind"];
    const data = row["data"];
    if (kind === "llm") {
        return deserializeLlm(data);
    }
    return deserializeObserve(data);
}
function deserializeObserve(data) {
    return {
        spanId: data["spanId"],
        traceId: data["traceId"],
        parentSpanId: data["parentSpanId"] ?? null,
        startedAt: parseDate(data["startedAt"]),
        endedAt: parseDate(data["endedAt"]),
        durationMs: data["durationMs"],
        name: data["name"] ?? null,
        input: data["input"],
        output: data["output"],
        metadata: data["metadata"] ?? {},
        error: data["error"] ?? null,
    };
}
function deserializeLlm(data) {
    const inputMessages = data["inputMessages"] ?? [];
    const outputMessages = data["outputMessages"] ?? [];
    const toolDefs = data["toolDefinitions"] ?? [];
    const finishReasons = data["finishReasons"] ?? [];
    return {
        spanId: data["spanId"],
        traceId: data["traceId"],
        parentSpanId: data["parentSpanId"] ?? null,
        startedAt: parseDate(data["startedAt"]),
        endedAt: parseDate(data["endedAt"]),
        durationMs: data["durationMs"],
        operation: data["operation"],
        provider: data["provider"],
        requestModel: data["requestModel"],
        responseModel: data["responseModel"] ?? null,
        inputTokens: data["inputTokens"],
        outputTokens: data["outputTokens"],
        cacheReadTokens: data["cacheReadTokens"],
        cacheCreationTokens: data["cacheCreationTokens"],
        requestTemperature: data["requestTemperature"] ?? null,
        requestMaxTokens: data["requestMaxTokens"] ?? null,
        requestTopP: data["requestTopP"] ?? null,
        finishReasons,
        responseId: data["responseId"] ?? null,
        outputType: data["outputType"] ?? null,
        errorType: data["errorType"] ?? null,
        inputMessages: inputMessages.map(deserializeMessage),
        outputMessages: outputMessages.map(deserializeAssistantMessage),
        toolDefinitions: toolDefs.map(deserializeToolDefinition),
    };
}
// ── Message deserialization ──────────────────────────────────────────────────
function deserializeMessage(m) {
    const role = m["role"];
    if (role === "system") {
        return { role: "system", content: m["content"] };
    }
    if (role === "user") {
        const content = m["content"].map(deserializeContent);
        return { role: "user", content };
    }
    if (role === "assistant") {
        return deserializeAssistantMessage(m);
    }
    if (role === "tool") {
        return {
            role: "tool",
            content: m["content"],
            toolCallId: m["toolCallId"] ?? null,
            toolName: m["toolName"] ?? null,
        };
    }
    throw new Error(`Unknown message role: ${role}`);
}
function deserializeAssistantMessage(m) {
    const content = m["content"].map(deserializeContent);
    const toolCalls = (m["toolCalls"] ?? []).map(deserializeToolCall);
    return {
        role: "assistant",
        content,
        toolCalls,
        finishReason: m["finishReason"] ?? null,
    };
}
function deserializeContent(c) {
    const ctype = c["type"];
    if (ctype === "text") {
        return { type: "text", text: c["text"] };
    }
    if (ctype === "image") {
        return {
            type: "image",
            url: c["url"],
            detail: c["detail"] ?? null,
        };
    }
    throw new Error(`Unknown content type: ${ctype}`);
}
function deserializeToolCall(tc) {
    return {
        name: tc["name"],
        arguments: tc["arguments"] ?? {},
        id: tc["id"] ?? null,
    };
}
function deserializeToolDefinition(td) {
    return {
        name: td["name"],
        description: td["description"] ?? null,
        parameters: td["parameters"] ?? null,
    };
}
// ── Utilities ────────────────────────────────────────────────────────────────
function parseDate(value) {
    if (value instanceof Date)
        return value;
    if (typeof value === "string") {
        const d = new Date(value);
        if (isNaN(d.getTime())) {
            throw new Error(`Invalid ISO 8601 date string: ${value}. ` +
                "Expected format: YYYY-MM-DDTHH:mm:ss.sssZ");
        }
        return d;
    }
    throw new Error(`Cannot parse date from: ${String(value)}`);
}
//# sourceMappingURL=serialization.js.map