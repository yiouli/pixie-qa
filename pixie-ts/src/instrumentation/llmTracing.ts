/**
 * pixie.instrumentation.llmTracing — LLM call tracing and span processing.
 *
 * TypeScript port of the Python llm_tracing module. Since there's no TS
 * equivalent of OpenInference instrumentors, we provide a simplified API
 * that can be fed LLM span data directly.
 */

/** Plain text content part. */
export interface TextContent {
  readonly text: string;
  readonly type: "text";
}

/** Image content part (URL or data URI). */
export interface ImageContent {
  readonly url: string;
  readonly detail?: string | null;
  readonly type: "image";
}

export type MessageContent = TextContent | ImageContent;

/** Tool invocation requested by the model. */
export interface ToolCall {
  readonly name: string;
  readonly arguments: Record<string, unknown>;
  readonly id?: string | null;
}

/** Tool made available to the model in the request. */
export interface ToolDefinition {
  readonly name: string;
  readonly description?: string | null;
  readonly parameters?: Record<string, unknown> | null;
}

/** System prompt message. */
export interface SystemMessage {
  readonly content: string;
  readonly role: "system";
}

/** User message with multimodal content parts. */
export interface UserMessage {
  readonly content: readonly MessageContent[];
  readonly role: "user";
}

/** Assistant response message with optional tool calls. */
export interface AssistantMessage {
  readonly content: readonly MessageContent[];
  readonly toolCalls: readonly ToolCall[];
  readonly finishReason?: string | null;
  readonly role: "assistant";
}

/** Tool execution result message. */
export interface ToolResultMessage {
  readonly content: string;
  readonly toolCallId?: string | null;
  readonly toolName?: string | null;
  readonly role: "tool";
}

export type Message =
  | SystemMessage
  | UserMessage
  | AssistantMessage
  | ToolResultMessage;

/** Create a UserMessage with a single TextContent part. */
export function userMessageFromText(text: string): UserMessage {
  return { content: [{ text, type: "text" }], role: "user" };
}

/** One LLM provider call. */
export interface LLMSpan {
  // Identity
  readonly spanId: string;
  readonly traceId: string;
  readonly parentSpanId: string | null;

  // Timing
  readonly startedAt: Date;
  readonly endedAt: Date;
  readonly durationMs: number;

  // Provider/model
  readonly operation: string;
  readonly provider: string;
  readonly requestModel: string;
  readonly responseModel: string | null;

  // Token usage
  readonly inputTokens: number;
  readonly outputTokens: number;
  readonly cacheReadTokens: number;
  readonly cacheCreationTokens: number;

  // Request parameters
  readonly requestTemperature: number | null;
  readonly requestMaxTokens: number | null;
  readonly requestTopP: number | null;

  // Response metadata
  readonly finishReasons: readonly string[];
  readonly responseId: string | null;
  readonly outputType: string | null;
  readonly errorType: string | null;

  // Content
  readonly inputMessages: readonly Message[];
  readonly outputMessages: readonly AssistantMessage[];
  readonly toolDefinitions: readonly ToolDefinition[];
}

/** A user-defined instrumented block. */
export interface ObserveSpan {
  readonly spanId: string;
  readonly traceId: string;
  readonly parentSpanId: string | null;
  readonly startedAt: Date;
  readonly endedAt: Date;
  readonly durationMs: number;
  readonly name: string | null;
  readonly input: unknown;
  readonly output: unknown;
  readonly metadata: Record<string, unknown>;
  readonly error: string | null;
}

// ── InstrumentationHandler ──────────────────────────────────────────

/**
 * Base class for instrumentation handlers.
 * Override onLlm or onObserve to receive span data.
 */
export class InstrumentationHandler {
  async onLlm(_span: LLMSpan): Promise<void> {}
  async onObserve(_span: ObserveSpan): Promise<void> {}
}

class HandlerRegistry extends InstrumentationHandler {
  private handlers: InstrumentationHandler[] = [];

  add(handler: InstrumentationHandler): void {
    this.handlers.push(handler);
  }

  remove(handler: InstrumentationHandler): void {
    const idx = this.handlers.indexOf(handler);
    if (idx === -1) throw new Error("Handler not found");
    this.handlers.splice(idx, 1);
  }

  async onLlm(span: LLMSpan): Promise<void> {
    const results = await Promise.allSettled(
      this.handlers.map((h) => h.onLlm(span)),
    );
    for (const r of results) {
      if (r.status === "rejected") {
        console.error("Handler onLlm error:", r.reason);
      }
    }
  }

  async onObserve(span: ObserveSpan): Promise<void> {
    const results = await Promise.allSettled(
      this.handlers.map((h) => h.onObserve(span)),
    );
    for (const r of results) {
      if (r.status === "rejected") {
        console.error("Handler onObserve error:", r.reason);
      }
    }
  }
}

// ── Module-level state ──────────────────────────────────────────────

const _registry = new HandlerRegistry();
let _initialized = false;

/**
 * Set up LLM tracing. Idempotent.
 */
export function enableLlmTracing(opts?: {
  captureContent?: boolean;
  queueSize?: number;
}): void {
  void opts;
  if (_initialized) return;
  _initialized = true;
}

/** Register handler to receive spans. */
export function addHandler(handler: InstrumentationHandler): void {
  _registry.add(handler);
}

/** Unregister handler. */
export function removeHandler(handler: InstrumentationHandler): void {
  _registry.remove(handler);
}

/** Submit an LLM span to all registered handlers. */
export async function submitLlmSpan(span: LLMSpan): Promise<void> {
  await _registry.onLlm(span);
}

/** Submit an observe span to all registered handlers. */
export async function submitObserveSpan(span: ObserveSpan): Promise<void> {
  await _registry.onObserve(span);
}

/**
 * Flush pending spans. Returns true if successful within timeout.
 */
export async function flush(_timeoutSeconds: number = 5.0): Promise<boolean> {
  // In the TS version, handlers are called synchronously via await,
  // so there's nothing to flush. This is a no-op for API compatibility.
  return true;
}
