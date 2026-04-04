/**
 * Evaluable model and span-to-evaluable conversion.
 *
 * `Evaluable` is an immutable interface that serves as the uniform
 * data carrier for evaluators. The `UNSET` sentinel distinguishes
 * "expected output was never provided" from "expected output is
 * explicitly null/undefined".
 */

import type {
  AssistantMessage,
  LLMSpan,
  ObserveSpan,
  TextContent,
} from "../instrumentation/spans";

// ── JSON value type ──────────────────────────────────────────────────────────

/**
 * Any value that can be represented in JSON.
 */
export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

// ── UNSET sentinel ───────────────────────────────────────────────────────────

/**
 * Sentinel to distinguish "not provided" from `null` / `undefined`.
 */
export const UNSET: unique symbol = Symbol("UNSET");
export type Unset = typeof UNSET;

// ── Evaluable interface ──────────────────────────────────────────────────────

/**
 * Uniform data carrier for evaluators.
 *
 * All fields use `JsonValue` to guarantee JSON round-trip fidelity.
 * `expectedOutput` uses a union with the `UNSET` sentinel so callers
 * can distinguish "expected output was not provided" from "expected
 * output is explicitly null".
 */
export interface Evaluable {
  readonly evalInput: JsonValue;
  readonly evalOutput: JsonValue;
  readonly evalMetadata: Record<string, JsonValue> | null;
  readonly expectedOutput: JsonValue | Unset;
  readonly evaluators: readonly string[] | null;
  readonly description: string | null;
}

// ── Factory / conversion ─────────────────────────────────────────────────────

function makeJsonCompatible(obj: unknown): JsonValue {
  if (obj === null || obj === undefined) return null;
  if (typeof obj === "string" || typeof obj === "number" || typeof obj === "boolean") {
    return obj;
  }
  if (Array.isArray(obj)) {
    return obj.map(makeJsonCompatible);
  }
  if (typeof obj === "object") {
    const result: Record<string, JsonValue> = {};
    for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
      result[k] = makeJsonCompatible(v);
    }
    return result;
  }
  return null;
}

function observeSpanToEvaluable(span: ObserveSpan): Evaluable {
  const meta: Record<string, JsonValue> = span.metadata
    ? { ...(makeJsonCompatible(span.metadata) as Record<string, JsonValue>) }
    : {};
  meta["trace_id"] = span.traceId;
  meta["span_id"] = span.spanId;
  return {
    evalInput: makeJsonCompatible(span.input),
    evalOutput: makeJsonCompatible(span.output),
    evalMetadata: meta,
    expectedOutput: UNSET,
    evaluators: null,
    description: null,
  };
}

function llmSpanToEvaluable(span: LLMSpan): Evaluable {
  // Extract text from last output message
  let outputText: string | null = null;
  if (span.outputMessages.length > 0) {
    const last: AssistantMessage =
      span.outputMessages[span.outputMessages.length - 1];
    const parts = last.content
      .filter((p): p is TextContent => p.type === "text")
      .map((p) => p.text);
    outputText = parts.length > 0 ? parts.join("") : null;
  }

  const inputData: JsonValue = span.inputMessages.map((msg) =>
    makeJsonCompatible(msg)
  );

  const metadata: Record<string, JsonValue> = {
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
    tool_definitions: span.toolDefinitions.map((td) =>
      makeJsonCompatible(td)
    ),
  };

  return {
    evalInput: inputData,
    evalOutput: outputText,
    evalMetadata: metadata,
    expectedOutput: UNSET,
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
export function asEvaluable(span: ObserveSpan | LLMSpan): Evaluable {
  if ("operation" in span) {
    return llmSpanToEvaluable(span);
  }
  return observeSpanToEvaluable(span);
}
