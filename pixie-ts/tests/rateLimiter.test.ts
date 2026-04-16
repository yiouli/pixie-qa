import { describe, it, expect, beforeEach } from "vitest";
import {
  EvalRateLimiter,
  configureRateLimits,
  getRateLimiter,
} from "../src/eval/rateLimiter.js";

beforeEach(() => {
  // Reset singleton state
  configureRateLimits(null);
});

describe("EvalRateLimiter", () => {
  it("creates with config", () => {
    const limiter = new EvalRateLimiter({
      rps: 4,
      rpm: 50,
      tps: 10_000,
      tpm: 500_000,
    });
    expect(limiter.config.rps).toBe(4);
    expect(limiter.config.rpm).toBe(50);
  });

  it("estimates tokens using len/3", () => {
    const limiter = new EvalRateLimiter({
      rps: 4,
      rpm: 50,
      tps: 10_000,
      tpm: 500_000,
    });
    expect(limiter.estimateTokens("abc")).toBe(1); // 3/3
    expect(limiter.estimateTokens("abcdef")).toBe(2); // 6/3
    expect(limiter.estimateTokens("")).toBe(0);
  });

  it("acquire resolves immediately when under limits", async () => {
    const limiter = new EvalRateLimiter({
      rps: 10,
      rpm: 100,
      tps: 50_000,
      tpm: 500_000,
    });
    // Should not hang
    await limiter.acquire(100);
  });
});

describe("configureRateLimits", () => {
  it("sets the singleton when given a config", () => {
    configureRateLimits({ rps: 2, rpm: 20, tps: 5000, tpm: 100_000 });
    const limiter = getRateLimiter();
    expect(limiter).not.toBeNull();
    expect(limiter!.config.rps).toBe(2);
  });

  it("clears the singleton when given null", () => {
    configureRateLimits({ rps: 2, rpm: 20, tps: 5000, tpm: 100_000 });
    configureRateLimits(null);
    const limiter = getRateLimiter();
    expect(limiter).toBeNull();
  });
});
