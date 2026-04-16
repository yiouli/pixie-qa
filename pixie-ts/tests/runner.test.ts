import { describe, it, expect } from "vitest";
import {
  resolveEvaluatorName,
  BUILTIN_EVALUATOR_NAMES,
} from "../src/harness/runner.js";

describe("resolveEvaluatorName", () => {
  it("resolves built-in names to pixie. prefix", () => {
    expect(resolveEvaluatorName("ExactMatch")).toBe("pixie.ExactMatch");
    expect(resolveEvaluatorName("Factuality")).toBe("pixie.Factuality");
  });

  it("passes through custom file: references", () => {
    expect(resolveEvaluatorName("./my_eval.js:MyEval")).toBe(
      "./my_eval.js:MyEval",
    );
  });

  it("throws for unknown bare names", () => {
    expect(() => resolveEvaluatorName("NonExistent")).toThrow(
      "Unknown evaluator",
    );
  });

  it("trims whitespace before resolving", () => {
    expect(resolveEvaluatorName("  ExactMatch  ")).toBe("pixie.ExactMatch");
  });

  it("knows all 21 builtin evaluators", () => {
    expect(BUILTIN_EVALUATOR_NAMES.size).toBe(21);
    for (const name of [
      "LevenshteinMatch",
      "ExactMatch",
      "NumericDiff",
      "JSONDiff",
      "ValidJSON",
      "ListContains",
      "EmbeddingSimilarity",
      "Factuality",
      "ClosedQA",
      "Battle",
      "Humor",
      "Security",
      "Sql",
      "Summary",
      "Translation",
      "Possible",
      "Moderation",
      "ContextRelevancy",
      "Faithfulness",
      "AnswerRelevancy",
      "AnswerCorrectness",
    ]) {
      expect(BUILTIN_EVALUATOR_NAMES.has(name)).toBe(true);
    }
  });
});
