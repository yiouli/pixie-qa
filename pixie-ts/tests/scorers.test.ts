import { describe, it, expect, beforeEach } from "vitest";
import {
  LevenshteinMatch,
  ExactMatch,
  NumericDiff,
  JSONDiff,
  ValidJSON,
  ListContains,
} from "../src/eval/scorers.js";
import { createEvaluable } from "../src/eval/evaluable.js";

function makeEvaluable(output: unknown, expected: unknown) {
  return createEvaluable({
    evalInput: [{ name: "q", value: "question" as any }],
    evalOutput: [{ name: "a", value: output as any }],
    expectation: expected as any,
  });
}

describe("LevenshteinMatch", () => {
  const scorer = LevenshteinMatch();

  it("returns 1.0 for identical strings", async () => {
    const result = await scorer(makeEvaluable("hello", "hello"));
    expect(result.score).toBe(1.0);
  });

  it("returns 1.0 for both empty", async () => {
    const result = await scorer(makeEvaluable("", ""));
    expect(result.score).toBe(1.0);
  });

  it("returns partial score for similar strings", async () => {
    const result = await scorer(makeEvaluable("kitten", "sitting"));
    expect(result.score).toBeGreaterThan(0);
    expect(result.score).toBeLessThan(1);
  });

  it("returns 0.0 for completely different strings", async () => {
    const result = await scorer(makeEvaluable("abc", "xyz"));
    expect(result.score).toBe(0);
  });
});

describe("ExactMatch", () => {
  const scorer = ExactMatch();

  it("returns 1.0 for matching values", async () => {
    const result = await scorer(makeEvaluable("hello", "hello"));
    expect(result.score).toBe(1.0);
  });

  it("returns 0.0 for non-matching values", async () => {
    const result = await scorer(makeEvaluable("hello", "world"));
    expect(result.score).toBe(0.0);
  });

  it("handles numeric match", async () => {
    const result = await scorer(makeEvaluable(42, 42));
    expect(result.score).toBe(1.0);
  });

  it("handles null values", async () => {
    const result = await scorer(makeEvaluable(null, null));
    expect(result.score).toBe(1.0);
  });
});

describe("NumericDiff", () => {
  const scorer = NumericDiff();

  it("returns 1.0 for identical numbers", async () => {
    const result = await scorer(makeEvaluable(42, 42));
    expect(result.score).toBe(1.0);
  });

  it("returns partial score for close numbers", async () => {
    const result = await scorer(makeEvaluable(90, 100));
    expect(result.score).toBeGreaterThan(0.8);
    expect(result.score).toBeLessThan(1.0);
  });

  it("returns 0.0 for non-numeric values", async () => {
    const result = await scorer(makeEvaluable("abc", "def"));
    expect(result.score).toBe(0.0);
  });
});

describe("JSONDiff", () => {
  const scorer = JSONDiff();

  it("returns 1.0 for matching JSON objects", async () => {
    const obj = { a: 1, b: "two" };
    const result = await scorer(makeEvaluable(obj, obj));
    expect(result.score).toBe(1.0);
  });

  it("returns 0.0 for different JSON objects", async () => {
    const result = await scorer(makeEvaluable({ a: 1 }, { a: 2 }));
    expect(result.score).toBe(0.0);
  });
});

describe("ValidJSON", () => {
  const scorer = ValidJSON();

  it("returns 1.0 for valid JSON string", async () => {
    const result = await scorer(makeEvaluable('{"key": "value"}', null));
    expect(result.score).toBe(1.0);
  });

  it("returns 1.0 for JSON-serializable objects", async () => {
    const result = await scorer(makeEvaluable({ key: "value" }, null));
    expect(result.score).toBe(1.0);
  });

  it("returns 0.0 for invalid JSON string", async () => {
    const result = await scorer(makeEvaluable("{invalid json", null));
    expect(result.score).toBe(0.0);
  });
});

describe("ListContains", () => {
  const scorer = ListContains();

  it("returns 1.0 when all expected items found", async () => {
    const result = await scorer(makeEvaluable([1, 2, 3], [1, 2]));
    expect(result.score).toBe(1.0);
  });

  it("returns 0.5 when half expected items found", async () => {
    const result = await scorer(makeEvaluable([1, 3], [1, 2]));
    expect(result.score).toBe(0.5);
  });

  it("returns 0.0 when no expected items found", async () => {
    const result = await scorer(makeEvaluable([4, 5], [1, 2]));
    expect(result.score).toBe(0.0);
  });

  it("returns 1.0 for empty expected list", async () => {
    const result = await scorer(makeEvaluable([1], []));
    expect(result.score).toBe(1.0);
  });
});
