import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
  getConfig,
  DEFAULT_ROOT,
  DEFAULT_RATE_LIMIT_RPS,
  DEFAULT_RATE_LIMIT_RPM,
  DEFAULT_RATE_LIMIT_TPS,
  DEFAULT_RATE_LIMIT_TPM,
} from "../src/config";

describe("getConfig", () => {
  const envBackup: Record<string, string | undefined> = {};
  const envKeys = [
    "PIXIE_ROOT",
    "PIXIE_DB_PATH",
    "PIXIE_DB_ENGINE",
    "PIXIE_DATASET_DIR",
    "PIXIE_RATE_LIMIT_ENABLED",
    "PIXIE_RATE_LIMIT_RPS",
    "PIXIE_RATE_LIMIT_RPM",
    "PIXIE_RATE_LIMIT_TPS",
    "PIXIE_RATE_LIMIT_TPM",
  ];

  beforeEach(() => {
    for (const key of envKeys) {
      envBackup[key] = process.env[key];
      delete process.env[key];
    }
  });

  afterEach(() => {
    for (const key of envKeys) {
      if (envBackup[key] === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = envBackup[key];
      }
    }
  });

  it("returns default values when no env vars are set", () => {
    const config = getConfig();
    expect(config.root).toBe(DEFAULT_ROOT);
    expect(config.dbPath).toContain("observations.db");
    expect(config.dbEngine).toBe("sqlite");
    expect(config.datasetDir).toContain("datasets");
    expect(config.rateLimits).toBeNull();
  });

  it("overrides root from PIXIE_ROOT", () => {
    process.env["PIXIE_ROOT"] = "custom_root";
    const config = getConfig();
    expect(config.root).toBe("custom_root");
    expect(config.dbPath).toContain("custom_root");
    expect(config.datasetDir).toContain("custom_root");
  });

  it("overrides dbPath from PIXIE_DB_PATH", () => {
    process.env["PIXIE_DB_PATH"] = "/some/db.sqlite";
    const config = getConfig();
    expect(config.dbPath).toBe("/some/db.sqlite");
  });

  it("overrides dbEngine from PIXIE_DB_ENGINE", () => {
    process.env["PIXIE_DB_ENGINE"] = "postgres";
    const config = getConfig();
    expect(config.dbEngine).toBe("postgres");
  });

  it("overrides datasetDir from PIXIE_DATASET_DIR", () => {
    process.env["PIXIE_DATASET_DIR"] = "/custom/datasets";
    const config = getConfig();
    expect(config.datasetDir).toBe("/custom/datasets");
  });

  it("enables rate limits when PIXIE_RATE_LIMIT_ENABLED=1", () => {
    process.env["PIXIE_RATE_LIMIT_ENABLED"] = "1";
    const config = getConfig();
    expect(config.rateLimits).not.toBeNull();
    expect(config.rateLimits!.rps).toBe(DEFAULT_RATE_LIMIT_RPS);
    expect(config.rateLimits!.rpm).toBe(DEFAULT_RATE_LIMIT_RPM);
    expect(config.rateLimits!.tps).toBe(DEFAULT_RATE_LIMIT_TPS);
    expect(config.rateLimits!.tpm).toBe(DEFAULT_RATE_LIMIT_TPM);
  });

  it("enables rate limits when PIXIE_RATE_LIMIT_ENABLED=true", () => {
    process.env["PIXIE_RATE_LIMIT_ENABLED"] = "true";
    const config = getConfig();
    expect(config.rateLimits).not.toBeNull();
  });

  it("disables rate limits when PIXIE_RATE_LIMIT_ENABLED=0", () => {
    process.env["PIXIE_RATE_LIMIT_ENABLED"] = "0";
    const config = getConfig();
    expect(config.rateLimits).toBeNull();
  });

  it("enables rate limits implicitly when an override is set", () => {
    process.env["PIXIE_RATE_LIMIT_RPS"] = "10";
    const config = getConfig();
    expect(config.rateLimits).not.toBeNull();
    expect(config.rateLimits!.rps).toBe(10);
  });

  it("overrides individual rate limit values", () => {
    process.env["PIXIE_RATE_LIMIT_ENABLED"] = "1";
    process.env["PIXIE_RATE_LIMIT_RPS"] = "8";
    process.env["PIXIE_RATE_LIMIT_RPM"] = "100";
    process.env["PIXIE_RATE_LIMIT_TPS"] = "20000";
    process.env["PIXIE_RATE_LIMIT_TPM"] = "1000000";
    const config = getConfig();
    expect(config.rateLimits).toEqual({
      rps: 8,
      rpm: 100,
      tps: 20000,
      tpm: 1000000,
    });
  });

  it("falls back to defaults for invalid float env vars", () => {
    process.env["PIXIE_RATE_LIMIT_ENABLED"] = "1";
    process.env["PIXIE_RATE_LIMIT_RPS"] = "not-a-number";
    const config = getConfig();
    expect(config.rateLimits!.rps).toBe(DEFAULT_RATE_LIMIT_RPS);
  });
});
