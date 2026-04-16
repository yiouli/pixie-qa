import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
  getConfig,
  DEFAULT_ROOT,
  DEFAULT_RATE_LIMIT_RPS,
  DEFAULT_RATE_LIMIT_RPM,
} from "../src/config.js";

describe("getConfig", () => {
  const originalEnv = { ...process.env };

  afterEach(() => {
    // Restore environment
    for (const key of Object.keys(process.env)) {
      if (key.startsWith("PIXIE_")) {
        delete process.env[key];
      }
    }
    Object.assign(process.env, originalEnv);
  });

  it("returns defaults when no env vars set", () => {
    // Clear any leftover PIXIE_ vars
    for (const key of Object.keys(process.env)) {
      if (key.startsWith("PIXIE_")) delete process.env[key];
    }
    const config = getConfig();
    expect(config.root).toBe(DEFAULT_ROOT);
    expect(config.datasetDir).toContain("datasets");
    expect(config.rateLimits).toBeNull();
    expect(config.traceOutput).toBeNull();
    expect(config.tracingEnabled).toBe(false);
  });

  it("reads PIXIE_ROOT from environment", () => {
    process.env["PIXIE_ROOT"] = "/tmp/custom_root";
    const config = getConfig();
    expect(config.root).toBe("/tmp/custom_root");
  });

  it("reads PIXIE_DATASET_DIR from environment", () => {
    process.env["PIXIE_DATASET_DIR"] = "/custom/datasets";
    const config = getConfig();
    expect(config.datasetDir).toBe("/custom/datasets");
  });

  it("enables tracing when PIXIE_TRACING=1", () => {
    process.env["PIXIE_TRACING"] = "1";
    const config = getConfig();
    expect(config.tracingEnabled).toBe(true);
  });

  it("enables tracing when PIXIE_TRACING=true (case-insensitive)", () => {
    process.env["PIXIE_TRACING"] = "True";
    const config = getConfig();
    expect(config.tracingEnabled).toBe(true);
  });

  it("reads trace output path", () => {
    process.env["PIXIE_TRACE_OUTPUT"] = "/tmp/traces.jsonl";
    const config = getConfig();
    expect(config.traceOutput).toBe("/tmp/traces.jsonl");
  });

  it("builds rate limits when enabled", () => {
    process.env["PIXIE_RATE_LIMIT_ENABLED"] = "1";
    const config = getConfig();
    expect(config.rateLimits).not.toBeNull();
    expect(config.rateLimits!.rps).toBe(DEFAULT_RATE_LIMIT_RPS);
    expect(config.rateLimits!.rpm).toBe(DEFAULT_RATE_LIMIT_RPM);
  });

  it("returns null rate limits when explicitly disabled", () => {
    process.env["PIXIE_RATE_LIMIT_ENABLED"] = "0";
    process.env["PIXIE_RATE_LIMIT_RPS"] = "10";
    const config = getConfig();
    expect(config.rateLimits).toBeNull();
  });

  it("auto-enables rate limits when overrides are present", () => {
    process.env["PIXIE_RATE_LIMIT_RPS"] = "10";
    const config = getConfig();
    expect(config.rateLimits).not.toBeNull();
    expect(config.rateLimits!.rps).toBe(10);
  });
});
