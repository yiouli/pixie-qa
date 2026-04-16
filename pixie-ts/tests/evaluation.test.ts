import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  evaluate,
  type Evaluation,
  type Evaluator,
} from "../src/eval/evaluation.js";
import { createEvaluable } from "../src/eval/evaluable.js";
import { configureRateLimits } from "../src/eval/rateLimiter.js";

// Disable rate limiter for unit tests
beforeEach(() => {
  configureRateLimits(null);
});

function makeEvaluable() {
  return createEvaluable({
    evalInput: [{ name: "q", value: "What is 2+2?" }],
    evalOutput: [{ name: "a", value: "4" }],
    expectation: "4",
  });
}

describe("evaluate", () => {
  it("returns evaluator result when score is in range", async () => {
    const evaluator: Evaluator = async () => ({
      score: 0.8,
      reasoning: "Good",
      details: {},
    });
    const result = await evaluate(evaluator, makeEvaluable());
    expect(result.score).toBe(0.8);
    expect(result.reasoning).toBe("Good");
  });

  it("clamps score above 1.0", async () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const evaluator: Evaluator = async () => ({
      score: 1.5,
      reasoning: "Over",
      details: {},
    });
    const result = await evaluate(evaluator, makeEvaluable());
    expect(result.score).toBe(1.0);
    expect(warnSpy).toHaveBeenCalled();
    warnSpy.mockRestore();
  });

  it("clamps score below 0.0", async () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const evaluator: Evaluator = async () => ({
      score: -0.5,
      reasoning: "Under",
      details: {},
    });
    const result = await evaluate(evaluator, makeEvaluable());
    expect(result.score).toBe(0.0);
    expect(warnSpy).toHaveBeenCalled();
    warnSpy.mockRestore();
  });

  it("propagates evaluator errors", async () => {
    const evaluator: Evaluator = async () => {
      throw new Error("Evaluator failed");
    };
    await expect(evaluate(evaluator, makeEvaluable())).rejects.toThrow(
      "Evaluator failed",
    );
  });
});
