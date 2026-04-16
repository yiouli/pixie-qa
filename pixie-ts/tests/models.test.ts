import { describe, it, expect } from "vitest";
import {
  INPUT_DATA_KEY,
  createInputDataLog,
  createLlmSpanLog,
  type InputDataLog,
  type LLMSpanLog,
} from "../src/instrumentation/models.js";

describe("INPUT_DATA_KEY", () => {
  it("equals input_data", () => {
    expect(INPUT_DATA_KEY).toBe("input_data");
  });
});

describe("createInputDataLog", () => {
  it("creates a kwargs-typed record", () => {
    const log = createInputDataLog({ question: "hello" });
    expect(log.type).toBe("kwargs");
    expect(log.value).toEqual({ question: "hello" });
  });
});

describe("createLlmSpanLog", () => {
  it("creates with defaults when no opts", () => {
    const log = createLlmSpanLog();
    expect(log.type).toBe("llm_span");
    expect(log.operation).toBeNull();
    expect(log.provider).toBeNull();
    expect(log.inputMessages).toEqual([]);
    expect(log.outputMessages).toEqual([]);
    expect(log.toolDefinitions).toEqual([]);
    expect(log.finishReasons).toEqual([]);
  });

  it("accepts partial overrides", () => {
    const log = createLlmSpanLog({
      operation: "chat",
      provider: "openai",
      requestModel: "gpt-4o",
      finishReasons: ["stop"],
    });
    expect(log.operation).toBe("chat");
    expect(log.provider).toBe("openai");
    expect(log.requestModel).toBe("gpt-4o");
    expect(log.finishReasons).toEqual(["stop"]);
    // non-overridden defaults
    expect(log.responseModel).toBeNull();
    expect(log.outputType).toBeNull();
  });
});
