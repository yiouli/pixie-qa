import { describe, it, expect } from "vitest";
import { UNSET, asEvaluable } from "../src/storage/evaluable";
import type { Evaluable } from "../src/storage/evaluable";
import type { ObserveSpan, LLMSpan } from "../src/instrumentation/spans";

// ── Test helpers ─────────────────────────────────────────────────────────────

function makeObserveSpan(overrides: Partial<ObserveSpan> = {}): ObserveSpan {
  return {
    spanId: "obs-1",
    traceId: "trace-1",
    parentSpanId: null,
    startedAt: new Date("2024-01-01T00:00:00Z"),
    endedAt: new Date("2024-01-01T00:00:01Z"),
    durationMs: 1000,
    name: "test-span",
    input: "hello",
    output: "world",
    metadata: { key: "val" },
    error: null,
    ...overrides,
  };
}

function makeLLMSpan(overrides: Partial<LLMSpan> = {}): LLMSpan {
  return {
    spanId: "llm-1",
    traceId: "trace-1",
    parentSpanId: null,
    startedAt: new Date("2024-01-01T00:00:00Z"),
    endedAt: new Date("2024-01-01T00:00:01Z"),
    durationMs: 1000,
    operation: "chat",
    provider: "openai",
    requestModel: "gpt-4",
    responseModel: "gpt-4-0613",
    inputTokens: 10,
    outputTokens: 20,
    cacheReadTokens: 0,
    cacheCreationTokens: 0,
    requestTemperature: null,
    requestMaxTokens: null,
    requestTopP: null,
    finishReasons: ["stop"],
    responseId: null,
    outputType: null,
    errorType: null,
    inputMessages: [
      { role: "user", content: [{ type: "text", text: "Hello" }] },
    ],
    outputMessages: [
      {
        role: "assistant",
        content: [{ type: "text", text: "Hi there" }],
        toolCalls: [],
        finishReason: "stop",
      },
    ],
    toolDefinitions: [],
    ...overrides,
  };
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("UNSET sentinel", () => {
  it("is a unique symbol", () => {
    expect(typeof UNSET).toBe("symbol");
    expect(UNSET.toString()).toContain("UNSET");
  });

  it("is not equal to null or undefined", () => {
    expect(UNSET as unknown).not.toBe(null);
    expect(UNSET as unknown).not.toBe(undefined);
  });
});

describe("Evaluable interface", () => {
  it("can be created manually", () => {
    const ev: Evaluable = {
      evalInput: "input text",
      evalOutput: "output text",
      evalMetadata: { key: "value" },
      expectedOutput: UNSET,
      evaluators: null,
      description: null,
    };
    expect(ev.evalInput).toBe("input text");
    expect(ev.expectedOutput).toBe(UNSET);
  });

  it("supports explicit null expectedOutput", () => {
    const ev: Evaluable = {
      evalInput: "input",
      evalOutput: "output",
      evalMetadata: null,
      expectedOutput: null,
      evaluators: ["eval1"],
      description: "test desc",
    };
    expect(ev.expectedOutput).toBeNull();
    expect(ev.expectedOutput).not.toBe(UNSET);
  });
});

describe("asEvaluable", () => {
  describe("from ObserveSpan", () => {
    it("converts input and output fields", () => {
      const span = makeObserveSpan({ input: "q", output: "a" });
      const ev = asEvaluable(span);
      expect(ev.evalInput).toBe("q");
      expect(ev.evalOutput).toBe("a");
    });

    it("sets expectedOutput to UNSET", () => {
      const ev = asEvaluable(makeObserveSpan());
      expect(ev.expectedOutput).toBe(UNSET);
    });

    it("includes trace_id and span_id in metadata", () => {
      const span = makeObserveSpan({ traceId: "t1", spanId: "s1" });
      const ev = asEvaluable(span);
      expect(ev.evalMetadata).not.toBeNull();
      expect(ev.evalMetadata!["trace_id"]).toBe("t1");
      expect(ev.evalMetadata!["span_id"]).toBe("s1");
    });

    it("merges span metadata into evalMetadata", () => {
      const span = makeObserveSpan({ metadata: { foo: "bar" } });
      const ev = asEvaluable(span);
      expect(ev.evalMetadata!["foo"]).toBe("bar");
    });

    it("handles null input and output", () => {
      const span = makeObserveSpan({ input: null, output: null });
      const ev = asEvaluable(span);
      expect(ev.evalInput).toBeNull();
      expect(ev.evalOutput).toBeNull();
    });
  });

  describe("from LLMSpan", () => {
    it("extracts output text from last assistant message", () => {
      const ev = asEvaluable(makeLLMSpan());
      expect(ev.evalOutput).toBe("Hi there");
    });

    it("sets expectedOutput to UNSET", () => {
      const ev = asEvaluable(makeLLMSpan());
      expect(ev.expectedOutput).toBe(UNSET);
    });

    it("includes provider and model info in metadata", () => {
      const ev = asEvaluable(makeLLMSpan());
      expect(ev.evalMetadata!["provider"]).toBe("openai");
      expect(ev.evalMetadata!["request_model"]).toBe("gpt-4");
      expect(ev.evalMetadata!["response_model"]).toBe("gpt-4-0613");
    });

    it("includes token counts in metadata", () => {
      const ev = asEvaluable(makeLLMSpan());
      expect(ev.evalMetadata!["input_tokens"]).toBe(10);
      expect(ev.evalMetadata!["output_tokens"]).toBe(20);
    });

    it("returns null output when no output messages exist", () => {
      const span = makeLLMSpan({ outputMessages: [] });
      const ev = asEvaluable(span);
      expect(ev.evalOutput).toBeNull();
    });

    it("serializes input messages as evalInput array", () => {
      const ev = asEvaluable(makeLLMSpan());
      expect(Array.isArray(ev.evalInput)).toBe(true);
    });
  });
});
