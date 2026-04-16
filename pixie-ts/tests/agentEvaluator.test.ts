import { describe, it, expect } from "vitest";
import {
  AgentEvaluationPending,
  createAgentEvaluator,
} from "../src/eval/agentEvaluator.js";
import { createEvaluable } from "../src/eval/evaluable.js";

describe("AgentEvaluationPending", () => {
  it("is an Error subclass with evaluatorName and criteria", () => {
    const err = new AgentEvaluationPending("MyEval", "check tone");
    expect(err).toBeInstanceOf(Error);
    expect(err.name).toBe("AgentEvaluationPending");
    expect(err.evaluatorName).toBe("MyEval");
    expect(err.criteria).toBe("check tone");
    expect(err.message).toContain("MyEval");
  });
});

describe("createAgentEvaluator", () => {
  it("returns a function named after the evaluator", () => {
    const fn = createAgentEvaluator("ToneCheck", "Check professional tone");
    expect(fn.name).toBe("ToneCheck");
  });

  it("always throws AgentEvaluationPending when called", async () => {
    const fn = createAgentEvaluator("ToneCheck", "Check tone");
    const evaluable = createEvaluable({
      evalInput: [{ name: "q", value: "hi" }],
      evalOutput: [{ name: "a", value: "hello" }],
    });
    await expect(fn(evaluable)).rejects.toThrow(AgentEvaluationPending);
  });
});
