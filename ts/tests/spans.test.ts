import { describe, it, expect } from "vitest";
import {
  createTextContent,
  createImageContent,
  createSystemMessage,
  createUserMessageFromText,
  createUserMessage,
  createAssistantMessage,
  createToolResultMessage,
} from "../src/instrumentation/spans";
import type {
  LLMSpan,
  ObserveSpan,
  TextContent,
  ImageContent,
} from "../src/instrumentation/spans";

// ── Content factory tests ────────────────────────────────────────────────────

describe("createTextContent", () => {
  it("creates a TextContent with type text", () => {
    const tc = createTextContent("hello");
    expect(tc.type).toBe("text");
    expect(tc.text).toBe("hello");
  });
});

describe("createImageContent", () => {
  it("creates an ImageContent with null detail by default", () => {
    const ic = createImageContent("https://example.com/img.png");
    expect(ic.type).toBe("image");
    expect(ic.url).toBe("https://example.com/img.png");
    expect(ic.detail).toBeNull();
  });

  it("accepts an explicit detail value", () => {
    const ic = createImageContent("https://example.com/img.png", "high");
    expect(ic.detail).toBe("high");
  });
});

// ── Message factory tests ────────────────────────────────────────────────────

describe("createSystemMessage", () => {
  it("creates a system message", () => {
    const msg = createSystemMessage("You are helpful.");
    expect(msg.role).toBe("system");
    expect(msg.content).toBe("You are helpful.");
  });
});

describe("createUserMessageFromText", () => {
  it("wraps a plain string into a UserMessage with TextContent", () => {
    const msg = createUserMessageFromText("What is 2+2?");
    expect(msg.role).toBe("user");
    expect(msg.content).toHaveLength(1);
    expect(msg.content[0].type).toBe("text");
    expect((msg.content[0] as TextContent).text).toBe("What is 2+2?");
  });
});

describe("createUserMessage", () => {
  it("creates a user message with mixed content", () => {
    const content = [
      createTextContent("Look at this:"),
      createImageContent("https://example.com/photo.jpg"),
    ];
    const msg = createUserMessage(content);
    expect(msg.role).toBe("user");
    expect(msg.content).toHaveLength(2);
    expect(msg.content[0].type).toBe("text");
    expect(msg.content[1].type).toBe("image");
  });
});

describe("createAssistantMessage", () => {
  it("creates an assistant message with defaults", () => {
    const msg = createAssistantMessage({
      content: [createTextContent("Sure!")],
      toolCalls: [],
    });
    expect(msg.role).toBe("assistant");
    expect(msg.content).toHaveLength(1);
    expect(msg.toolCalls).toHaveLength(0);
    expect(msg.finishReason).toBeNull();
  });

  it("includes tool calls and finish reason", () => {
    const msg = createAssistantMessage({
      content: [],
      toolCalls: [{ name: "search", arguments: { q: "test" }, id: "tc-1" }],
      finishReason: "tool_calls",
    });
    expect(msg.toolCalls).toHaveLength(1);
    expect(msg.toolCalls[0].name).toBe("search");
    expect(msg.finishReason).toBe("tool_calls");
  });
});

describe("createToolResultMessage", () => {
  it("creates a tool result message with defaults", () => {
    const msg = createToolResultMessage({ content: "result data" });
    expect(msg.role).toBe("tool");
    expect(msg.content).toBe("result data");
    expect(msg.toolCallId).toBeNull();
    expect(msg.toolName).toBeNull();
  });

  it("accepts optional toolCallId and toolName", () => {
    const msg = createToolResultMessage({
      content: "42",
      toolCallId: "tc-1",
      toolName: "calculator",
    });
    expect(msg.toolCallId).toBe("tc-1");
    expect(msg.toolName).toBe("calculator");
  });
});

// ── Span type tests ──────────────────────────────────────────────────────────

describe("ObserveSpan", () => {
  it("can be created as a plain object", () => {
    const span: ObserveSpan = {
      spanId: "s1",
      traceId: "t1",
      parentSpanId: null,
      startedAt: new Date("2024-01-01T00:00:00Z"),
      endedAt: new Date("2024-01-01T00:00:01Z"),
      durationMs: 1000,
      name: "my-observation",
      input: { question: "What?" },
      output: { answer: "42" },
      metadata: { env: "test" },
      error: null,
    };
    expect(span.name).toBe("my-observation");
    expect(span.durationMs).toBe(1000);
    expect(span.error).toBeNull();
  });
});

describe("LLMSpan", () => {
  it("can be created as a plain object", () => {
    const span: LLMSpan = {
      spanId: "llm-1",
      traceId: "t1",
      parentSpanId: "s1",
      startedAt: new Date("2024-01-01T00:00:00Z"),
      endedAt: new Date("2024-01-01T00:00:02Z"),
      durationMs: 2000,
      operation: "chat",
      provider: "anthropic",
      requestModel: "claude-3-opus",
      responseModel: "claude-3-opus-20240229",
      inputTokens: 100,
      outputTokens: 50,
      cacheReadTokens: 0,
      cacheCreationTokens: 0,
      requestTemperature: 0.7,
      requestMaxTokens: 1024,
      requestTopP: null,
      finishReasons: ["end_turn"],
      responseId: "resp-1",
      outputType: null,
      errorType: null,
      inputMessages: [createSystemMessage("Be helpful")],
      outputMessages: [
        createAssistantMessage({
          content: [createTextContent("Hello!")],
          toolCalls: [],
          finishReason: "end_turn",
        }),
      ],
      toolDefinitions: [
        { name: "search", description: "Search the web", parameters: null },
      ],
    };
    expect(span.operation).toBe("chat");
    expect(span.provider).toBe("anthropic");
    expect(span.inputTokens).toBe(100);
    expect(span.toolDefinitions).toHaveLength(1);
  });
});
