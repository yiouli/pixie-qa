import { describe, it, expect, vi } from "vitest";
import {
  InstrumentationHandler,
  addHandler,
  removeHandler,
  submitLlmSpan,
  submitObserveSpan,
  flush,
  userMessageFromText,
  type LLMSpan,
  type ObserveSpan,
} from "../src/instrumentation/llmTracing.js";

function makeLlmSpan(overrides: Partial<LLMSpan> = {}): LLMSpan {
  return {
    spanId: "span-1",
    traceId: "trace-1",
    parentSpanId: null,
    startedAt: new Date("2024-01-01T00:00:00Z"),
    endedAt: new Date("2024-01-01T00:00:01Z"),
    durationMs: 1000,
    operation: "chat",
    provider: "openai",
    requestModel: "gpt-4o-mini",
    responseModel: "gpt-4o-mini",
    inputTokens: 100,
    outputTokens: 50,
    cacheReadTokens: 0,
    cacheCreationTokens: 0,
    requestTemperature: 0.7,
    requestMaxTokens: null,
    requestTopP: null,
    finishReasons: ["stop"],
    responseId: null,
    outputType: null,
    errorType: null,
    inputMessages: [],
    outputMessages: [],
    toolDefinitions: [],
    ...overrides,
  };
}

function makeObserveSpan(overrides: Partial<ObserveSpan> = {}): ObserveSpan {
  return {
    spanId: "span-2",
    traceId: "trace-1",
    parentSpanId: null,
    startedAt: new Date("2024-01-01T00:00:00Z"),
    endedAt: new Date("2024-01-01T00:00:01Z"),
    durationMs: 1000,
    name: "process",
    input: { q: "hello" },
    output: { a: "world" },
    metadata: {},
    error: null,
    ...overrides,
  };
}

describe("userMessageFromText", () => {
  it("creates a UserMessage with single TextContent", () => {
    const msg = userMessageFromText("hello");
    expect(msg.role).toBe("user");
    expect(msg.content).toHaveLength(1);
    expect(msg.content[0].type).toBe("text");
    expect((msg.content[0] as any).text).toBe("hello");
  });
});

describe("InstrumentationHandler + registry", () => {
  it("handler receives LLM spans", async () => {
    const handler = new InstrumentationHandler();
    const spy = vi.spyOn(handler, "onLlm");
    addHandler(handler);

    const span = makeLlmSpan();
    await submitLlmSpan(span);

    expect(spy).toHaveBeenCalledWith(span);
    removeHandler(handler);
  });

  it("handler receives observe spans", async () => {
    const handler = new InstrumentationHandler();
    const spy = vi.spyOn(handler, "onObserve");
    addHandler(handler);

    const span = makeObserveSpan();
    await submitObserveSpan(span);

    expect(spy).toHaveBeenCalledWith(span);
    removeHandler(handler);
  });

  it("removing a handler stops delivery", async () => {
    const handler = new InstrumentationHandler();
    const spy = vi.spyOn(handler, "onLlm");
    addHandler(handler);
    removeHandler(handler);

    await submitLlmSpan(makeLlmSpan());
    expect(spy).not.toHaveBeenCalled();
  });

  it("removes only the requested handler", () => {
    const h1 = new InstrumentationHandler();
    const h2 = new InstrumentationHandler();
    addHandler(h1);
    addHandler(h2);
    removeHandler(h1);
    // h2 should still be there — no throw
    removeHandler(h2);
  });

  it("throws when removing a handler not in registry", () => {
    const handler = new InstrumentationHandler();
    expect(() => removeHandler(handler)).toThrow("Handler not found");
  });

  it("handler errors are swallowed (logged to console.error)", async () => {
    const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const handler = new InstrumentationHandler();
    vi.spyOn(handler, "onLlm").mockRejectedValue(new Error("boom"));
    addHandler(handler);

    await submitLlmSpan(makeLlmSpan());
    expect(errSpy).toHaveBeenCalled();

    removeHandler(handler);
    errSpy.mockRestore();
  });
});

describe("flush", () => {
  it("returns true (no-op in TS)", async () => {
    const result = await flush();
    expect(result).toBe(true);
  });
});
