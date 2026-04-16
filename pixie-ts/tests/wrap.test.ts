import { describe, it, expect } from "vitest";
import {
  wrap,
  setEvalInput,
  getEvalInput,
  clearEvalInput,
  initEvalOutput,
  getEvalOutput,
  clearEvalOutput,
  runWithWrapContext,
  runWithWrapContextAsync,
  WrapRegistryMissError,
  filterByPurpose,
  serializeWrapData,
  type WrappedData,
} from "../src/instrumentation/wrap.js";

describe("serializeWrapData", () => {
  it("round-trips simple values", () => {
    expect(serializeWrapData(42)).toBe(42);
    expect(serializeWrapData("hello")).toBe("hello");
    expect(serializeWrapData(null)).toBeNull();
  });

  it("round-trips objects", () => {
    expect(serializeWrapData({ a: 1 })).toEqual({ a: 1 });
  });
});

describe("filterByPurpose", () => {
  const entries: WrappedData[] = [
    {
      type: "wrap",
      name: "a",
      purpose: "input",
      data: "1",
      description: null,
      traceId: null,
      spanId: null,
    },
    {
      type: "wrap",
      name: "b",
      purpose: "output",
      data: "2",
      description: null,
      traceId: null,
      spanId: null,
    },
    {
      type: "wrap",
      name: "c",
      purpose: "state",
      data: "3",
      description: null,
      traceId: null,
      spanId: null,
    },
  ];

  it("filters to matching purposes", () => {
    const result = filterByPurpose(entries, new Set(["input"]));
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe("a");
  });

  it("supports multiple purposes", () => {
    const result = filterByPurpose(entries, new Set(["input", "output"]));
    expect(result).toHaveLength(2);
  });
});

describe("wrap with eval context", () => {
  it("wrap purpose=input returns from registry when available", () => {
    runWithWrapContext(() => {
      const reg = new Map<string, any>([["user_query", "from registry"]]);
      setEvalInput(reg);

      const result = wrap("original", { purpose: "input", name: "user_query" });
      expect(result).toBe("from registry");
      clearEvalInput();
    });
  });

  it("wrap purpose=input returns original when no registry", () => {
    runWithWrapContext(() => {
      const result = wrap("original", { purpose: "input", name: "user_query" });
      expect(result).toBe("original");
    });
  });

  it("wrap purpose=input throws WrapRegistryMissError for missing key", () => {
    runWithWrapContext(() => {
      const reg = new Map<string, any>([["other_key", "value"]]);
      setEvalInput(reg);

      expect(() =>
        wrap("original", { purpose: "input", name: "missing_key" }),
      ).toThrow(WrapRegistryMissError);
      clearEvalInput();
    });
  });

  it("wrap purpose=output captures to eval output", () => {
    runWithWrapContext(() => {
      initEvalOutput();
      const result = wrap("answer", { purpose: "output", name: "response" });
      expect(result).toBe("answer");

      const output = getEvalOutput();
      expect(output).toHaveLength(1);
      expect(output![0]["name"]).toBe("response");
      expect(output![0]["data"]).toBe("answer");
      clearEvalOutput();
    });
  });

  it("wrap purpose=state captures to eval output", () => {
    runWithWrapContext(() => {
      initEvalOutput();
      wrap({ step: 1 }, { purpose: "state", name: "progress" });

      const output = getEvalOutput();
      expect(output).toHaveLength(1);
      expect(output![0]["name"]).toBe("progress");
      clearEvalOutput();
    });
  });
});

describe("runWithWrapContextAsync", () => {
  it("provides isolated context", async () => {
    const result = await runWithWrapContextAsync(async () => {
      initEvalOutput();
      wrap("test", { purpose: "output", name: "x" });
      const output = getEvalOutput();
      return output?.length ?? 0;
    });
    expect(result).toBe(1);
  });
});
