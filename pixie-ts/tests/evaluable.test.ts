import { describe, it, expect } from "vitest";
import {
  UNSET,
  createTestCase,
  createEvaluable,
  collapseNamedData,
  type NamedData,
} from "../src/eval/evaluable.js";

describe("createTestCase", () => {
  it("returns defaults when no options", () => {
    const tc = createTestCase({});
    expect(tc.evalInput).toEqual([]);
    expect(tc.expectation).toBe(UNSET);
    expect(tc.evalMetadata).toBeNull();
    expect(tc.description).toBeNull();
  });

  it("accepts all fields", () => {
    const tc = createTestCase({
      evalInput: [{ name: "q", value: "hello" }],
      expectation: "world",
      evalMetadata: { key: "val" },
      description: "test case",
    });
    expect(tc.evalInput).toHaveLength(1);
    expect(tc.expectation).toBe("world");
    expect(tc.evalMetadata).toEqual({ key: "val" });
    expect(tc.description).toBe("test case");
  });
});

describe("createEvaluable", () => {
  it("throws if evalInput is empty", () => {
    expect(() =>
      createEvaluable({
        evalInput: [],
        evalOutput: [{ name: "a", value: "b" }],
      }),
    ).toThrow("evalInput must be non-empty");
  });

  it("throws if evalOutput is empty", () => {
    expect(() =>
      createEvaluable({
        evalInput: [{ name: "a", value: "b" }],
        evalOutput: [],
      }),
    ).toThrow("evalOutput must be non-empty");
  });

  it("creates evaluable with valid inputs", () => {
    const ev = createEvaluable({
      evalInput: [{ name: "q", value: "hello" }],
      evalOutput: [{ name: "a", value: "world" }],
      expectation: "world",
    });
    expect(ev.evalInput).toHaveLength(1);
    expect(ev.evalOutput).toHaveLength(1);
    expect(ev.expectation).toBe("world");
  });
});

describe("collapseNamedData", () => {
  it("returns null for empty list", () => {
    expect(collapseNamedData([])).toBeNull();
  });

  it("returns single value for one item", () => {
    const items: NamedData[] = [{ name: "x", value: 42 }];
    expect(collapseNamedData(items)).toBe(42);
  });

  it("returns dict for multiple items", () => {
    const items: NamedData[] = [
      { name: "a", value: 1 },
      { name: "b", value: 2 },
    ];
    expect(collapseNamedData(items)).toEqual({ a: 1, b: 2 });
  });
});
