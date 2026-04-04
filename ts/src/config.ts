/**
 * Centralized configuration with env var and `.env` overrides.
 *
 * All environment variables are prefixed with `PIXIE_`. `getConfig()` loads
 * the nearest `.env` from the current working directory at call time, while
 * preserving any variables already present in `process.env`. Values are
 * resolved at call time rather than import time so tests can safely
 * manipulate the process environment before calling `getConfig()`.
 */

import dotenv from "dotenv";
import path from "path";
import fs from "fs";

// ── Defaults ─────────────────────────────────────────────────────────────────

export const DEFAULT_ROOT = "pixie_qa";
export const DEFAULT_RATE_LIMIT_RPS = 4.0;
export const DEFAULT_RATE_LIMIT_RPM = 50.0;
export const DEFAULT_RATE_LIMIT_TPS = 10_000;
export const DEFAULT_RATE_LIMIT_TPM = 500_000;

const TRUE_ENV_VALUES = new Set(["1", "true", "yes", "on"]);

// ── Interfaces ───────────────────────────────────────────────────────────────

/**
 * Configuration for evaluator rate limiting.
 */
export interface RateLimitConfig {
  readonly rps: number;
  readonly rpm: number;
  readonly tps: number;
  readonly tpm: number;
}

/**
 * Immutable configuration snapshot.
 *
 * All paths default to subdirectories / files within a single `pixie_qa`
 * project folder so that observations, datasets, tests, scripts and notes
 * live in one predictable location.
 */
export interface PixieConfig {
  readonly root: string;
  readonly dbPath: string;
  readonly dbEngine: string;
  readonly datasetDir: string;
  readonly rateLimits: RateLimitConfig | null;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function isTruthyEnv(value: string): boolean {
  return TRUE_ENV_VALUES.has(value.trim().toLowerCase());
}

function getFloatEnv(name: string, defaultValue: number): number {
  const raw = process.env[name];
  if (raw === undefined) {
    return defaultValue;
  }
  const parsed = parseFloat(raw);
  return Number.isNaN(parsed) ? defaultValue : parsed;
}

function getRateLimitConfig(): RateLimitConfig | null {
  const enabledValue = process.env["PIXIE_RATE_LIMIT_ENABLED"];
  const hasOverrides = [
    "PIXIE_RATE_LIMIT_RPS",
    "PIXIE_RATE_LIMIT_RPM",
    "PIXIE_RATE_LIMIT_TPS",
    "PIXIE_RATE_LIMIT_TPM",
  ].some((name) => process.env[name] !== undefined);

  if (enabledValue !== undefined && !isTruthyEnv(enabledValue)) {
    return null;
  }
  if (enabledValue === undefined && !hasOverrides) {
    return null;
  }

  return {
    rps: getFloatEnv("PIXIE_RATE_LIMIT_RPS", DEFAULT_RATE_LIMIT_RPS),
    rpm: getFloatEnv("PIXIE_RATE_LIMIT_RPM", DEFAULT_RATE_LIMIT_RPM),
    tps: getFloatEnv("PIXIE_RATE_LIMIT_TPS", DEFAULT_RATE_LIMIT_TPS),
    tpm: getFloatEnv("PIXIE_RATE_LIMIT_TPM", DEFAULT_RATE_LIMIT_TPM),
  };
}

/**
 * Find the nearest `.env` file starting from `cwd` and walking up.
 */
function findDotenv(): string | undefined {
  let dir = process.cwd();
  while (true) {
    const candidate = path.join(dir, ".env");
    if (fs.existsSync(candidate)) {
      return candidate;
    }
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return undefined;
}

// ── Public API ───────────────────────────────────────────────────────────────

/**
 * Read configuration from environment variables with defaults.
 *
 * Supported variables:
 * - `PIXIE_ROOT` — overrides `root`
 * - `PIXIE_DB_PATH` — overrides `dbPath`
 * - `PIXIE_DB_ENGINE` — overrides `dbEngine`
 * - `PIXIE_DATASET_DIR` — overrides `datasetDir`
 * - `PIXIE_RATE_LIMIT_ENABLED` — enables evaluator rate limiting
 * - `PIXIE_RATE_LIMIT_RPS` — overrides `rateLimits.rps`
 * - `PIXIE_RATE_LIMIT_RPM` — overrides `rateLimits.rpm`
 * - `PIXIE_RATE_LIMIT_TPS` — overrides `rateLimits.tps`
 * - `PIXIE_RATE_LIMIT_TPM` — overrides `rateLimits.tpm`
 */
export function getConfig(): PixieConfig {
  // Load .env without overriding existing env vars
  const envPath = findDotenv();
  if (envPath) {
    dotenv.config({ path: envPath, override: false });
  }

  const root = process.env["PIXIE_ROOT"] ?? DEFAULT_ROOT;
  return {
    root,
    dbPath: process.env["PIXIE_DB_PATH"] ?? path.join(root, "observations.db"),
    dbEngine: process.env["PIXIE_DB_ENGINE"] ?? "sqlite",
    datasetDir:
      process.env["PIXIE_DATASET_DIR"] ?? path.join(root, "datasets"),
    rateLimits: getRateLimitConfig(),
  };
}
