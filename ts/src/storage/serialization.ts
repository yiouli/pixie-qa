/**
 * Span serialization and deserialization for database storage.
 *
 * Handles conversion between readonly span interfaces and plain objects
 * suitable for SQLite table rows, including nested types and Date↔ISO
 * string conversion.
 */

import type {
  AssistantMessage,
  ImageContent,
  LLMSpan,
  Message,
  MessageContent,
  ObserveSpan,
  SystemMessage,
  TextContent,
  ToolCall,
  ToolDefinition,
  ToolResultMessage,
  UserMessage,
} from "../instrumentation/spans";

// ── Serialize ────────────────────────────────────────────────────────────────

/**
 * Convert a span to a dict matching the Observation table columns.
 */
export function serializeSpan(
  span: ObserveSpan | LLMSpan
): Record<string, unknown> {
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
function toPlainObject(obj: unknown): unknown {
  if (obj === null || obj === undefined) return null;
  if (obj instanceof Date) return obj.toISOString();
  if (typeof obj === "string" || typeof obj === "number" || typeof obj === "boolean") {
    return obj;
  }
  if (Array.isArray(obj)) {
    return obj.map(toPlainObject);
  }
  if (typeof obj === "object") {
    const result: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
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
export function deserializeSpan(
  row: Record<string, unknown>
): ObserveSpan | LLMSpan {
  const kind = row["span_kind"] as string;
  const data = row["data"] as Record<string, unknown>;

  if (kind === "llm") {
    return deserializeLlm(data);
  }
  return deserializeObserve(data);
}

function deserializeObserve(data: Record<string, unknown>): ObserveSpan {
  return {
    spanId: data["spanId"] as string,
    traceId: data["traceId"] as string,
    parentSpanId: (data["parentSpanId"] as string | null) ?? null,
    startedAt: parseDate(data["startedAt"]),
    endedAt: parseDate(data["endedAt"]),
    durationMs: data["durationMs"] as number,
    name: (data["name"] as string | null) ?? null,
    input: data["input"],
    output: data["output"],
    metadata: (data["metadata"] as Readonly<Record<string, unknown>>) ?? {},
    error: (data["error"] as string | null) ?? null,
  };
}

function deserializeLlm(data: Record<string, unknown>): LLMSpan {
  const inputMessages = (data["inputMessages"] as Record<string, unknown>[]) ?? [];
  const outputMessages = (data["outputMessages"] as Record<string, unknown>[]) ?? [];
  const toolDefs = (data["toolDefinitions"] as Record<string, unknown>[]) ?? [];
  const finishReasons = (data["finishReasons"] as string[]) ?? [];

  return {
    spanId: data["spanId"] as string,
    traceId: data["traceId"] as string,
    parentSpanId: (data["parentSpanId"] as string | null) ?? null,
    startedAt: parseDate(data["startedAt"]),
    endedAt: parseDate(data["endedAt"]),
    durationMs: data["durationMs"] as number,
    operation: data["operation"] as string,
    provider: data["provider"] as string,
    requestModel: data["requestModel"] as string,
    responseModel: (data["responseModel"] as string | null) ?? null,
    inputTokens: data["inputTokens"] as number,
    outputTokens: data["outputTokens"] as number,
    cacheReadTokens: data["cacheReadTokens"] as number,
    cacheCreationTokens: data["cacheCreationTokens"] as number,
    requestTemperature: (data["requestTemperature"] as number | null) ?? null,
    requestMaxTokens: (data["requestMaxTokens"] as number | null) ?? null,
    requestTopP: (data["requestTopP"] as number | null) ?? null,
    finishReasons,
    responseId: (data["responseId"] as string | null) ?? null,
    outputType: (data["outputType"] as string | null) ?? null,
    errorType: (data["errorType"] as string | null) ?? null,
    inputMessages: inputMessages.map(deserializeMessage),
    outputMessages: outputMessages.map(deserializeAssistantMessage),
    toolDefinitions: toolDefs.map(deserializeToolDefinition),
  };
}

// ── Message deserialization ──────────────────────────────────────────────────

function deserializeMessage(m: Record<string, unknown>): Message {
  const role = m["role"] as string;
  if (role === "system") {
    return { role: "system", content: m["content"] as string } as SystemMessage;
  }
  if (role === "user") {
    const content = (m["content"] as Record<string, unknown>[]).map(deserializeContent);
    return { role: "user", content } as UserMessage;
  }
  if (role === "assistant") {
    return deserializeAssistantMessage(m);
  }
  if (role === "tool") {
    return {
      role: "tool",
      content: m["content"] as string,
      toolCallId: (m["toolCallId"] as string | null) ?? null,
      toolName: (m["toolName"] as string | null) ?? null,
    } as ToolResultMessage;
  }
  throw new Error(`Unknown message role: ${role}`);
}

function deserializeAssistantMessage(
  m: Record<string, unknown>
): AssistantMessage {
  const content = (m["content"] as Record<string, unknown>[]).map(deserializeContent);
  const toolCalls = ((m["toolCalls"] as Record<string, unknown>[]) ?? []).map(
    deserializeToolCall
  );
  return {
    role: "assistant",
    content,
    toolCalls,
    finishReason: (m["finishReason"] as string | null) ?? null,
  };
}

function deserializeContent(
  c: Record<string, unknown>
): TextContent | ImageContent {
  const ctype = c["type"] as string;
  if (ctype === "text") {
    return { type: "text", text: c["text"] as string };
  }
  if (ctype === "image") {
    return {
      type: "image",
      url: c["url"] as string,
      detail: (c["detail"] as string | null) ?? null,
    };
  }
  throw new Error(`Unknown content type: ${ctype}`);
}

function deserializeToolCall(tc: Record<string, unknown>): ToolCall {
  return {
    name: tc["name"] as string,
    arguments: (tc["arguments"] as Record<string, unknown>) ?? {},
    id: (tc["id"] as string | null) ?? null,
  };
}

function deserializeToolDefinition(td: Record<string, unknown>): ToolDefinition {
  return {
    name: td["name"] as string,
    description: (td["description"] as string | null) ?? null,
    parameters: (td["parameters"] as Record<string, unknown> | null) ?? null,
  };
}

// ── Utilities ────────────────────────────────────────────────────────────────

function parseDate(value: unknown): Date {
  if (value instanceof Date) return value;
  if (typeof value === "string") {
    const d = new Date(value);
    if (isNaN(d.getTime())) {
      throw new Error(
        `Invalid ISO 8601 date string: ${value}. ` +
          "Expected format: YYYY-MM-DDTHH:mm:ss.sssZ"
      );
    }
    return d;
  }
  throw new Error(`Cannot parse date from: ${String(value)}`);
}

export type { MessageContent };
