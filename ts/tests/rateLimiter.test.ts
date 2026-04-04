import { describe, it, expect, beforeEach } from "vitest";
import {
  EvalRateLimiter,
  configureRateLimits,
  getRateLimiter,
  _resetRateLimiter,
} from "../src/evals/rateLimiter";
import type { RateLimitConfig } from "../src/config";

// ── Test helpers ─────────────────────────────────────────────────────────────

const defaultConfig: RateLimitConfig = {
  rps: 4,
  rpm: 50,
  tps: 10_000,
  tpm: 500_000,
};

// ── EvalRateLimiter ──────────────────────────────────────────────────────────

describe("EvalRateLimiter", () => {
  it("stores its config", () => {
    const limiter = new EvalRateLimiter(defaultConfig);
    expect(limiter.config).toEqual(defaultConfig);
  });

  describe("estimateTokens", () => {
    it("estimates tokens as len/3", () => {
      const limiter = new EvalRateLimiter(defaultConfig);
      expect(limiter.estimateTokens("abcdef")).toBe(2);
      expect(limiter.estimateTokens("ab")).toBe(0);
      expect(limiter.estimateTokens("abcdefghi")).toBe(3);
    });

    it("returns 0 for empty string", () => {
      const limiter = new EvalRateLimiter(defaultConfig);
      expect(limiter.estimateTokens("")).toBe(0);
    });
  });

  describe("acquire", () => {
    it("resolves immediately when under limits", async () => {
      const limiter = new EvalRateLimiter({ ...defaultConfig, rps: 100, rpm: 1000 });
      // Should resolve very quickly
      const start = Date.now();
      await limiter.acquire(10);
      const elapsed = Date.now() - start;
      expect(elapsed).toBeLessThan(200);
    });

    it("records requests in sliding window", async () => {
      const limiter = new EvalRateLimiter({ ...defaultConfig, rps: 2, rpm: 100 });
      await limiter.acquire(0);
      await limiter.acquire(0);
      // Third request should be delayed (but we just verify it eventually resolves)
      const start = Date.now();
      await limiter.acquire(0);
      const elapsed = Date.now() - start;
      // Should have waited at least 50ms (the poll interval)
      expect(elapsed).toBeGreaterThanOrEqual(40);
    });
  });
});

// ── configureRateLimits / getRateLimiter ──────────────────────────────────────

describe("configureRateLimits", () => {
  beforeEach(() => {
    _resetRateLimiter();
  });

  it("sets a rate limiter when config is provided", () => {
    configureRateLimits(defaultConfig);
    const limiter = getRateLimiter();
    expect(limiter).not.toBeNull();
    expect(limiter!.config).toEqual(defaultConfig);
  });

  it("clears the rate limiter when null is passed", () => {
    configureRateLimits(defaultConfig);
    configureRateLimits(null);
    expect(getRateLimiter()).toBeNull();
  });
});

describe("getRateLimiter", () => {
  beforeEach(() => {
    _resetRateLimiter();
    // Clear env vars so config doesn't enable rate limiting
    delete process.env["PIXIE_RATE_LIMIT_ENABLED"];
    delete process.env["PIXIE_RATE_LIMIT_RPS"];
    delete process.env["PIXIE_RATE_LIMIT_RPM"];
    delete process.env["PIXIE_RATE_LIMIT_TPS"];
    delete process.env["PIXIE_RATE_LIMIT_TPM"];
  });

  it("returns null when no rate limiting is configured", () => {
    const limiter = getRateLimiter();
    expect(limiter).toBeNull();
  });

  it("auto-initializes from config on first call", () => {
    process.env["PIXIE_RATE_LIMIT_ENABLED"] = "1";
    _resetRateLimiter();
    const limiter = getRateLimiter();
    expect(limiter).not.toBeNull();
    delete process.env["PIXIE_RATE_LIMIT_ENABLED"];
  });
});
