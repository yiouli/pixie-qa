import { describe, it, expect, beforeEach } from "vitest";
import { createEvaluation, evaluate } from "../src/evals/evaluation";
import type { Evaluator, Evaluation } from "../src/evals/evaluation";
import type { Evaluable } from "../src/storage/evaluable";
import { UNSET } from "../src/storage/evaluable";
import { _resetRateLimiter } from "../src/evals/rateLimiter";

// ── Test helpers ─────────────────────────────────────────────────────────────

function makeEvaluable(overrides: Partial<Evaluable> = {}): Evaluable {
  return {
    evalInput: "What is 2+2?",
    evalOutput: "4",
    evalMetadata: null,
    expectedOutput: UNSET,
    evaluators: null,
    description: null,
    ...overrides,
  };
}

// ── createEvaluation ─────────────────────────────────────────────────────────

describe("createEvaluation", () => {
  it("creates an Evaluation with default empty details", () => {
    const ev = createEvaluation({ score: 0.9, reasoning: "Good" });
    expect(ev.score).toBe(0.9);
    expect(ev.reasoning).toBe("Good");
    expect(ev.details).toEqual({});
  });

  it("creates an Evaluation with custom details", () => {
    const ev = createEvaluation({
      score: 1.0,
      reasoning: "Perfect",
      details: { method: "exact_match" },
    });
    expect(ev.details).toEqual({ method: "exact_match" });
  });
});

// ── evaluate ─────────────────────────────────────────────────────────────────

describe("evaluate", () => {
  beforeEach(() => {
    _resetRateLimiter();
  });

  it("runs a sync evaluator", async () => {
    const syncEval: Evaluator = (ev) =>
      createEvaluation({ score: 0.8, reasoning: "sync result" });

    const result = await evaluate(syncEval, makeEvaluable());
    expect(result.score).toBe(0.8);
    expect(result.reasoning).toBe("sync result");
  });

  it("runs an async evaluator", async () => {
    const asyncEval: Evaluator = async (ev) =>
      createEvaluation({ score: 0.95, reasoning: "async result" });

    const result = await evaluate(asyncEval, makeEvaluable());
    expect(result.score).toBe(0.95);
    expect(result.reasoning).toBe("async result");
  });

  it("clamps score above 1.0 to 1.0", async () => {
    const overScorer: Evaluator = () =>
      createEvaluation({ score: 1.5, reasoning: "over" });

    const result = await evaluate(overScorer, makeEvaluable());
    expect(result.score).toBe(1.0);
  });

  it("clamps score below 0.0 to 0.0", async () => {
    const underScorer: Evaluator = () =>
      createEvaluation({ score: -0.3, reasoning: "under" });

    const result = await evaluate(underScorer, makeEvaluable());
    expect(result.score).toBe(0.0);
  });

  it("does not clamp scores in [0, 1] range", async () => {
    const normalScorer: Evaluator = () =>
      createEvaluation({ score: 0.5, reasoning: "normal" });

    const result = await evaluate(normalScorer, makeEvaluable());
    expect(result.score).toBe(0.5);
  });

  it("passes evaluable data to the evaluator", async () => {
    const checker: Evaluator = (ev) => {
      expect(ev.evalInput).toBe("test-input");
      expect(ev.evalOutput).toBe("test-output");
      return createEvaluation({ score: 1.0, reasoning: "checked" });
    };

    await evaluate(
      checker,
      makeEvaluable({ evalInput: "test-input", evalOutput: "test-output" })
    );
  });

  it("propagates evaluator errors", async () => {
    const failing: Evaluator = () => {
      throw new Error("Evaluator crashed");
    };

    await expect(evaluate(failing, makeEvaluable())).rejects.toThrow(
      "Evaluator crashed"
    );
  });

  it("preserves details through clamping", async () => {
    const detailedScorer: Evaluator = () =>
      createEvaluation({
        score: 2.0,
        reasoning: "over",
        details: { method: "test" },
      });

    const result = await evaluate(detailedScorer, makeEvaluable());
    expect(result.score).toBe(1.0);
    expect(result.details).toEqual({ method: "test" });
  });
});
