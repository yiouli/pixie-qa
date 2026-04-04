import { describe, it, expect } from "vitest";
import { lastLlmCall, root } from "../src/evals/traceHelpers";
import { ObservationNode } from "../src/storage/tree";
import { UNSET } from "../src/storage/evaluable";
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
    name: "root-span",
    input: "input text",
    output: "output text",
    metadata: {},
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
    durationMs: 500,
    operation: "chat",
    provider: "openai",
    requestModel: "gpt-4",
    responseModel: "gpt-4",
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
      { role: "user", content: [{ type: "text", text: "hi" }] },
    ],
    outputMessages: [
      {
        role: "assistant",
        content: [{ type: "text", text: "hello" }],
        toolCalls: [],
        finishReason: "stop",
      },
    ],
    toolDefinitions: [],
    ...overrides,
  };
}

// ── lastLlmCall ──────────────────────────────────────────────────────────────

describe("lastLlmCall", () => {
  it("returns the evaluable for the latest LLM span", () => {
    const rootNode = new ObservationNode(makeObserveSpan());
    const llm1 = new ObservationNode(
      makeLLMSpan({
        spanId: "llm-1",
        endedAt: new Date("2024-01-01T00:00:01Z"),
      })
    );
    const llm2 = new ObservationNode(
      makeLLMSpan({
        spanId: "llm-2",
        endedAt: new Date("2024-01-01T00:00:02Z"),
      })
    );
    rootNode.children = [llm1, llm2];

    const ev = lastLlmCall([rootNode]);
    expect(ev.evalMetadata).not.toBeNull();
    expect(ev.evalMetadata!["span_id"]).toBe("llm-2");
  });

  it("throws when no LLM spans exist in the trace", () => {
    const rootNode = new ObservationNode(makeObserveSpan());
    expect(() => lastLlmCall([rootNode])).toThrow("No LLMSpan found");
  });

  it("throws on empty trace", () => {
    expect(() => lastLlmCall([])).toThrow("No LLMSpan found");
  });

  it("finds LLM spans nested deep in the tree", () => {
    const rootNode = new ObservationNode(makeObserveSpan());
    const child = new ObservationNode(
      makeObserveSpan({ spanId: "child", name: "child" })
    );
    const deepLlm = new ObservationNode(
      makeLLMSpan({
        spanId: "deep-llm",
        endedAt: new Date("2024-01-01T00:00:05Z"),
      })
    );
    rootNode.children = [child];
    child.children = [deepLlm];

    const ev = lastLlmCall([rootNode]);
    expect(ev.evalMetadata!["span_id"]).toBe("deep-llm");
  });

  it("returns an evaluable with UNSET expectedOutput", () => {
    const llmNode = new ObservationNode(makeLLMSpan());
    const ev = lastLlmCall([llmNode]);
    expect(ev.expectedOutput).toBe(UNSET);
  });
});

// ── root ─────────────────────────────────────────────────────────────────────

describe("root", () => {
  it("returns the first root node as evaluable", () => {
    const rootNode = new ObservationNode(
      makeObserveSpan({ input: "root input", output: "root output" })
    );
    const ev = root([rootNode]);
    expect(ev.evalInput).toBe("root input");
    expect(ev.evalOutput).toBe("root output");
  });

  it("throws on empty trace", () => {
    expect(() => root([])).toThrow("Trace is empty");
  });

  it("returns the first root when multiple roots exist", () => {
    const r1 = new ObservationNode(
      makeObserveSpan({ spanId: "r1", input: "first" })
    );
    const r2 = new ObservationNode(
      makeObserveSpan({ spanId: "r2", input: "second" })
    );
    const ev = root([r1, r2]);
    expect(ev.evalInput).toBe("first");
  });

  it("works with an LLM span as root", () => {
    const llmNode = new ObservationNode(makeLLMSpan());
    const ev = root([llmNode]);
    // LLM spans produce array evalInput (input messages)
    expect(Array.isArray(ev.evalInput)).toBe(true);
  });
});
