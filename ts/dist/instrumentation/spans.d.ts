/**
 * Data model types for pixie instrumentation spans.
 *
 * All span types use readonly fields to enforce immutability, mirroring
 * the frozen dataclasses in the Python implementation.
 */
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
export type Message = SystemMessage | UserMessage | AssistantMessage | ToolResultMessage;
export declare function createTextContent(text: string): TextContent;
export declare function createImageContent(url: string, detail?: string | null): ImageContent;
export declare function createSystemMessage(content: string): SystemMessage;
export declare function createUserMessageFromText(text: string): UserMessage;
export declare function createUserMessage(content: readonly MessageContent[]): UserMessage;
export declare function createAssistantMessage(opts: {
    content: readonly MessageContent[];
    toolCalls: readonly ToolCall[];
    finishReason?: string | null;
}): AssistantMessage;
export declare function createToolResultMessage(opts: {
    content: string;
    toolCallId?: string | null;
    toolName?: string | null;
}): ToolResultMessage;
/**
 * One LLM provider call, produced by LLMSpanProcessor from
 * OpenInference attributes.
 */
export interface LLMSpan {
    readonly spanId: string;
    readonly traceId: string;
    readonly parentSpanId: string | null;
    readonly startedAt: Date;
    readonly endedAt: Date;
    readonly durationMs: number;
    readonly operation: string;
    readonly provider: string;
    readonly requestModel: string;
    readonly responseModel: string | null;
    readonly inputTokens: number;
    readonly outputTokens: number;
    readonly cacheReadTokens: number;
    readonly cacheCreationTokens: number;
    readonly requestTemperature: number | null;
    readonly requestMaxTokens: number | null;
    readonly requestTopP: number | null;
    readonly finishReasons: readonly string[];
    readonly responseId: string | null;
    readonly outputType: string | null;
    readonly errorType: string | null;
    readonly inputMessages: readonly Message[];
    readonly outputMessages: readonly AssistantMessage[];
    readonly toolDefinitions: readonly ToolDefinition[];
}
/**
 * A user-defined instrumented block, produced when a
 * startObservation() block exits.
 */
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
    readonly metadata: Readonly<Record<string, unknown>>;
    readonly error: string | null;
}
//# sourceMappingURL=spans.d.ts.map