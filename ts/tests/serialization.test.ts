import { describe, it, expect } from "vitest";
import {
  serializeSpan,
  deserializeSpan,
} from "../src/storage/serialization";
import type { ObserveSpan, LLMSpan } from "../src/instrumentation/spans";

// ── Test helpers ─────────────────────────────────────────────────────────────

function makeObserveSpan(overrides: Partial<ObserveSpan> = {}): ObserveSpan {
  return {
    spanId: "obs-1",
    traceId: "trace-1",
    parentSpanId: null,
    startedAt: new Date("2024-01-01T00:00:00.000Z"),
    endedAt: new Date("2024-01-01T00:00:01.000Z"),
    durationMs: 1000,
    name: "test-observe",
    input: { question: "What?" },
    output: { answer: "42" },
    metadata: { env: "test" },
    error: null,
    ...overrides,
  };
}

function makeLLMSpan(overrides: Partial<LLMSpan> = {}): LLMSpan {
  return {
    spanId: "llm-1",
    traceId: "trace-1",
    parentSpanId: "obs-1",
    startedAt: new Date("2024-06-15T10:00:00.000Z"),
    endedAt: new Date("2024-06-15T10:00:02.000Z"),
    durationMs: 2000,
    operation: "chat",
    provider: "openai",
    requestModel: "gpt-4o",
    responseModel: "gpt-4o-2024-05-13",
    inputTokens: 150,
    outputTokens: 75,
    cacheReadTokens: 50,
    cacheCreationTokens: 10,
    requestTemperature: 0.7,
    requestMaxTokens: 1024,
    requestTopP: 0.9,
    finishReasons: ["stop"],
    responseId: "resp-abc",
    outputType: null,
    errorType: null,
    inputMessages: [
      { role: "system", content: "You are helpful." },
      { role: "user", content: [{ type: "text", text: "Hello" }] },
    ],
    outputMessages: [
      {
        role: "assistant",
        content: [{ type: "text", text: "Hi there!" }],
        toolCalls: [],
        finishReason: "stop",
      },
    ],
    toolDefinitions: [
      { name: "search", description: "Search the web", parameters: { q: "string" } },
    ],
    ...overrides,
  };
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("serializeSpan", () => {
  describe("ObserveSpan", () => {
    it("produces a row with span_kind=observe", () => {
      const row = serializeSpan(makeObserveSpan());
      expect(row["span_kind"]).toBe("observe");
      expect(row["id"]).toBe("obs-1");
      expect(row["trace_id"]).toBe("trace-1");
      expect(row["name"]).toBe("test-observe");
    });

    it("serializes dates to ISO strings", () => {
      const row = serializeSpan(makeObserveSpan());
      expect(row["started_at"]).toBe("2024-01-01T00:00:00.000Z");
      expect(row["ended_at"]).toBe("2024-01-01T00:00:01.000Z");
    });

    it("includes duration_ms", () => {
      const row = serializeSpan(makeObserveSpan());
      expect(row["duration_ms"]).toBe(1000);
    });

    it("includes error field", () => {
      const row = serializeSpan(makeObserveSpan({ error: "fail" }));
      expect(row["error"]).toBe("fail");
    });
  });

  describe("LLMSpan", () => {
    it("produces a row with span_kind=llm", () => {
      const row = serializeSpan(makeLLMSpan());
      expect(row["span_kind"]).toBe("llm");
      expect(row["id"]).toBe("llm-1");
      expect(row["name"]).toBe("gpt-4o");
    });

    it("includes errorType in error field", () => {
      const row = serializeSpan(makeLLMSpan({ errorType: "timeout" }));
      expect(row["error"]).toBe("timeout");
    });
  });
});

describe("deserializeSpan", () => {
  describe("ObserveSpan round-trip", () => {
    it("round-trips an ObserveSpan through serialize/deserialize", () => {
      const original = makeObserveSpan();
      const row = serializeSpan(original);
      const restored = deserializeSpan(row) as ObserveSpan;

      expect(restored.spanId).toBe(original.spanId);
      expect(restored.traceId).toBe(original.traceId);
      expect(restored.parentSpanId).toBe(original.parentSpanId);
      expect(restored.durationMs).toBe(original.durationMs);
      expect(restored.name).toBe(original.name);
      expect(restored.error).toBe(original.error);
      expect(restored.startedAt.toISOString()).toBe(original.startedAt.toISOString());
      expect(restored.endedAt.toISOString()).toBe(original.endedAt.toISOString());
    });

    it("preserves input and output objects", () => {
      const original = makeObserveSpan({
        input: { nested: { deep: true } },
        output: [1, 2, 3],
      });
      const row = serializeSpan(original);
      const restored = deserializeSpan(row) as ObserveSpan;
      expect(restored.input).toEqual({ nested: { deep: true } });
      expect(restored.output).toEqual([1, 2, 3]);
    });

    it("preserves metadata", () => {
      const original = makeObserveSpan({ metadata: { foo: "bar", num: 42 } });
      const row = serializeSpan(original);
      const restored = deserializeSpan(row) as ObserveSpan;
      expect(restored.metadata).toEqual({ foo: "bar", num: 42 });
    });
  });

  describe("LLMSpan round-trip", () => {
    it("round-trips an LLMSpan through serialize/deserialize", () => {
      const original = makeLLMSpan();
      const row = serializeSpan(original);
      const restored = deserializeSpan(row) as LLMSpan;

      expect(restored.spanId).toBe(original.spanId);
      expect(restored.traceId).toBe(original.traceId);
      expect(restored.parentSpanId).toBe(original.parentSpanId);
      expect(restored.durationMs).toBe(original.durationMs);
      expect(restored.operation).toBe(original.operation);
      expect(restored.provider).toBe(original.provider);
      expect(restored.requestModel).toBe(original.requestModel);
      expect(restored.responseModel).toBe(original.responseModel);
    });

    it("preserves token counts", () => {
      const original = makeLLMSpan();
      const row = serializeSpan(original);
      const restored = deserializeSpan(row) as LLMSpan;
      expect(restored.inputTokens).toBe(150);
      expect(restored.outputTokens).toBe(75);
      expect(restored.cacheReadTokens).toBe(50);
      expect(restored.cacheCreationTokens).toBe(10);
    });

    it("preserves request parameters", () => {
      const original = makeLLMSpan();
      const row = serializeSpan(original);
      const restored = deserializeSpan(row) as LLMSpan;
      expect(restored.requestTemperature).toBe(0.7);
      expect(restored.requestMaxTokens).toBe(1024);
      expect(restored.requestTopP).toBe(0.9);
    });

    it("preserves messages", () => {
      const original = makeLLMSpan();
      const row = serializeSpan(original);
      const restored = deserializeSpan(row) as LLMSpan;
      expect(restored.inputMessages).toHaveLength(2);
      expect(restored.inputMessages[0].role).toBe("system");
      expect(restored.inputMessages[1].role).toBe("user");
      expect(restored.outputMessages).toHaveLength(1);
      expect(restored.outputMessages[0].role).toBe("assistant");
    });

    it("preserves tool definitions", () => {
      const original = makeLLMSpan();
      const row = serializeSpan(original);
      const restored = deserializeSpan(row) as LLMSpan;
      expect(restored.toolDefinitions).toHaveLength(1);
      expect(restored.toolDefinitions[0].name).toBe("search");
      expect(restored.toolDefinitions[0].description).toBe("Search the web");
    });

    it("preserves finishReasons", () => {
      const original = makeLLMSpan({ finishReasons: ["stop", "length"] });
      const row = serializeSpan(original);
      const restored = deserializeSpan(row) as LLMSpan;
      expect(restored.finishReasons).toEqual(["stop", "length"]);
    });

    it("round-trips tool calls in assistant messages", () => {
      const original = makeLLMSpan({
        outputMessages: [
          {
            role: "assistant",
            content: [{ type: "text", text: "" }],
            toolCalls: [
              { name: "search", arguments: { q: "test" }, id: "tc-1" },
            ],
            finishReason: "tool_calls",
          },
        ],
      });
      const row = serializeSpan(original);
      const restored = deserializeSpan(row) as LLMSpan;
      expect(restored.outputMessages[0].toolCalls).toHaveLength(1);
      expect(restored.outputMessages[0].toolCalls[0].name).toBe("search");
      expect(restored.outputMessages[0].toolCalls[0].id).toBe("tc-1");
    });

    it("round-trips tool result messages", () => {
      const original = makeLLMSpan({
        inputMessages: [
          {
            role: "tool",
            content: "result data",
            toolCallId: "tc-1",
            toolName: "search",
          },
        ],
      });
      const row = serializeSpan(original);
      const restored = deserializeSpan(row) as LLMSpan;
      expect(restored.inputMessages[0].role).toBe("tool");
    });

    it("round-trips image content", () => {
      const original = makeLLMSpan({
        inputMessages: [
          {
            role: "user",
            content: [
              { type: "image", url: "https://example.com/img.png", detail: "high" },
            ],
          },
        ],
      });
      const row = serializeSpan(original);
      const restored = deserializeSpan(row) as LLMSpan;
      const content = restored.inputMessages[0];
      expect(content.role).toBe("user");
      if (content.role === "user") {
        expect(content.content[0].type).toBe("image");
      }
    });
  });
});
