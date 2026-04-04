/**
 * Data model types for pixie instrumentation spans.
 *
 * All span types use readonly fields to enforce immutability, mirroring
 * the frozen dataclasses in the Python implementation.
 */

// ── Message content types ────────────────────────────────────────────────────

export interface TextContent {
  readonly type: "text";
  readonly text: string;
}

export interface ImageContent {
  readonly type: "image";
  readonly url: string;
  readonly detail: string | null;
}

export type MessageContent = TextContent | ImageContent;

// ── Tool types ───────────────────────────────────────────────────────────────

export interface ToolCall {
  readonly name: string;
  readonly arguments: Record<string, unknown>;
  readonly id: string | null;
}

export interface ToolDefinition {
  readonly name: string;
  readonly description: string | null;
  readonly parameters: Record<string, unknown> | null;
}

// ── Message types ────────────────────────────────────────────────────────────

export interface SystemMessage {
  readonly role: "system";
  readonly content: string;
}

export interface UserMessage {
  readonly role: "user";
  readonly content: readonly MessageContent[];
}

export interface AssistantMessage {
  readonly role: "assistant";
  readonly content: readonly MessageContent[];
  readonly toolCalls: readonly ToolCall[];
  readonly finishReason: string | null;
}

export interface ToolResultMessage {
  readonly role: "tool";
  readonly content: string;
  readonly toolCallId: string | null;
  readonly toolName: string | null;
}

export type Message =
  | SystemMessage
  | UserMessage
  | AssistantMessage
  | ToolResultMessage;

// ── Factory helpers ──────────────────────────────────────────────────────────

export function createTextContent(text: string): TextContent {
  return { type: "text", text };
}

export function createImageContent(
  url: string,
  detail: string | null = null
): ImageContent {
  return { type: "image", url, detail };
}

export function createSystemMessage(content: string): SystemMessage {
  return { role: "system", content };
}

export function createUserMessageFromText(text: string): UserMessage {
  return { role: "user", content: [createTextContent(text)] };
}

export function createUserMessage(
  content: readonly MessageContent[]
): UserMessage {
  return { role: "user", content };
}

export function createAssistantMessage(opts: {
  content: readonly MessageContent[];
  toolCalls: readonly ToolCall[];
  finishReason?: string | null;
}): AssistantMessage {
  return {
    role: "assistant",
    content: opts.content,
    toolCalls: opts.toolCalls,
    finishReason: opts.finishReason ?? null,
  };
}

export function createToolResultMessage(opts: {
  content: string;
  toolCallId?: string | null;
  toolName?: string | null;
}): ToolResultMessage {
  return {
    role: "tool",
    content: opts.content,
    toolCallId: opts.toolCallId ?? null,
    toolName: opts.toolName ?? null,
  };
}

// ── Span types ───────────────────────────────────────────────────────────────

/**
 * One LLM provider call, produced by LLMSpanProcessor from
 * OpenInference attributes.
 */
export interface LLMSpan {
  // Identity
  readonly spanId: string;
  readonly traceId: string;
  readonly parentSpanId: string | null;

  // Timing
  readonly startedAt: Date;
  readonly endedAt: Date;
  readonly durationMs: number;

  // Provider / model
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

/**
 * A user-defined instrumented block, produced when a
 * startObservation() block exits.
 */
export interface ObserveSpan {
  // Identity
  readonly spanId: string;
  readonly traceId: string;
  readonly parentSpanId: string | null;

  // Timing
  readonly startedAt: Date;
  readonly endedAt: Date;
  readonly durationMs: number;

  // User-defined fields
  readonly name: string | null;
  readonly input: unknown;
  readonly output: unknown;
  readonly metadata: Readonly<Record<string, unknown>>;
  readonly error: string | null;
}
