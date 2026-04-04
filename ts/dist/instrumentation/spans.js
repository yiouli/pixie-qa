"use strict";
/**
 * Data model types for pixie instrumentation spans.
 *
 * All span types use readonly fields to enforce immutability, mirroring
 * the frozen dataclasses in the Python implementation.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.createTextContent = createTextContent;
exports.createImageContent = createImageContent;
exports.createSystemMessage = createSystemMessage;
exports.createUserMessageFromText = createUserMessageFromText;
exports.createUserMessage = createUserMessage;
exports.createAssistantMessage = createAssistantMessage;
exports.createToolResultMessage = createToolResultMessage;
// ── Factory helpers ──────────────────────────────────────────────────────────
function createTextContent(text) {
    return { type: "text", text };
}
function createImageContent(url, detail = null) {
    return { type: "image", url, detail };
}
function createSystemMessage(content) {
    return { role: "system", content };
}
function createUserMessageFromText(text) {
    return { role: "user", content: [createTextContent(text)] };
}
function createUserMessage(content) {
    return { role: "user", content };
}
function createAssistantMessage(opts) {
    return {
        role: "assistant",
        content: opts.content,
        toolCalls: opts.toolCalls,
        finishReason: opts.finishReason ?? null,
    };
}
function createToolResultMessage(opts) {
    return {
        role: "tool",
        content: opts.content,
        toolCallId: opts.toolCallId ?? null,
        toolName: opts.toolName ?? null,
    };
}
//# sourceMappingURL=spans.js.map