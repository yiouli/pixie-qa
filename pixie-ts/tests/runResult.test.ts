import { describe, it, expect } from "vitest";
import {
  generateTestId,
  isEvaluationResult,
  entryInput,
  entryOutput,
  type EvaluationResult,
  type PendingEvaluation,
  type EntryResult,
} from "../src/harness/runResult.js";

describe("generateTestId", () => {
  it("returns a string in YYYYMMDD-HHMMSS format", () => {
    const id = generateTestId();
    expect(id).toMatch(/^\d{8}-\d{6}$/);
  });

  it("generates unique ids on subsequent calls", () => {
    const ids = new Set(Array.from({ length: 5 }, () => generateTestId()));
    // At minimum, they should be valid format (may collide within same second)
    for (const id of ids) {
      expect(id).toMatch(/^\d{8}-\d{6}$/);
    }
  });
});

describe("isEvaluationResult", () => {
  it("returns true for EvaluationResult", () => {
    const ev: EvaluationResult = {
      evaluator: "ExactMatch",
      score: 1.0,
      reasoning: "ok",
    };
    expect(isEvaluationResult(ev)).toBe(true);
  });

  it("returns false for PendingEvaluation", () => {
    const ev: PendingEvaluation = { evaluator: "AgentEval", criteria: "check" };
    expect(isEvaluationResult(ev)).toBe(false);
  });
});

describe("entryInput / entryOutput", () => {
  const entry: EntryResult = {
    evalInput: [{ name: "question", value: "What is 2+2?" }],
    evalOutput: [{ name: "answer", value: "4" }],
    evaluations: [],
    expectation: "4",
    evaluators: ["ExactMatch"],
    evalMetadata: null,
    description: null,
  };

  it("collapses input to single value", () => {
    expect(entryInput(entry)).toBe("What is 2+2?");
  });

  it("collapses output to single value", () => {
    expect(entryOutput(entry)).toBe("4");
  });

  it("collapses multiple inputs to dict", () => {
    const multiEntry: EntryResult = {
      ...entry,
      evalInput: [
        { name: "q1", value: "hello" },
        { name: "q2", value: "world" },
      ],
    };
    expect(entryInput(multiEntry)).toEqual({ q1: "hello", q2: "world" });
  });
});
