import { describe, it, expect } from "vitest";
import {
  isRunnableClass,
  getRunnableArgsSchema,
  type Runnable,
  type RunnableClass,
} from "../src/harness/runnable.js";
import { z } from "zod";

class TestRunnable implements Runnable<{ input: string }> {
  async setup(): Promise<void> {}
  async teardown(): Promise<void> {}
  async run(_args: { input: string }): Promise<void> {}
}

// isRunnableClass checks typeof obj.create === "function" on the constructor
// and typeof obj.prototype.run === "function", so we need a class that:
// 1) has a static create() method
// 2) has run() on its prototype
class TestRunnableClass {
  static argsSchema = z.object({ input: z.string() });

  static create(): Runnable<{ input: string }> {
    return new TestRunnable();
  }

  async setup(): Promise<void> {}
  async teardown(): Promise<void> {}
  async run(_args: { input: string }): Promise<void> {}
}

describe("isRunnableClass", () => {
  it("returns true for a valid RunnableClass", () => {
    expect(isRunnableClass(TestRunnableClass)).toBe(true);
  });

  it("returns false for a plain object", () => {
    expect(isRunnableClass({})).toBe(false);
  });

  it("returns false for null", () => {
    expect(isRunnableClass(null)).toBe(false);
  });

  it("returns false for a string", () => {
    expect(isRunnableClass("hello")).toBe(false);
  });

  it("returns false for a function without create/run", () => {
    function Bare() {}
    expect(isRunnableClass(Bare)).toBe(false);
  });
});

describe("getRunnableArgsSchema", () => {
  it("returns schema when present", () => {
    const schema = getRunnableArgsSchema(TestRunnableClass);
    expect(schema).not.toBeNull();
    const parsed = schema!.parse({ input: "hello" });
    expect(parsed).toEqual({ input: "hello" });
  });

  it("returns null when argsSchema is absent", () => {
    class NoSchema {
      static create() {
        return new TestRunnable();
      }
    }
    const schema = getRunnableArgsSchema(NoSchema as unknown as RunnableClass);
    expect(schema).toBeNull();
  });
});
