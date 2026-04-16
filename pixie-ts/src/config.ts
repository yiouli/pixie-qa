/**
 * pixie.config — Centralised configuration with env var and .env overrides.
 *
 * All environment variables are prefixed with PIXIE_. getConfig() loads
 * the nearest .env from the current working directory at call time.
 */

import { config as loadDotenv } from "dotenv";
import path from "node:path";

/** Default root directory for all pixie-generated artefacts. */
export const DEFAULT_ROOT = "pixie_qa";
export const DEFAULT_RATE_LIMIT_RPS = 4.0;
export const DEFAULT_RATE_LIMIT_RPM = 50.0;
export const DEFAULT_RATE_LIMIT_TPS = 10_000.0;
export const DEFAULT_RATE_LIMIT_TPM = 500_000.0;

const TRUE_ENV_VALUES = new Set(["1", "true", "yes", "on"]);

/** Configuration for evaluator rate limiting. */
export interface RateLimitConfig {
  readonly rps: number;
  readonly rpm: number;
  readonly tps: number;
  readonly tpm: number;
}

/** Immutable configuration snapshot. */
export interface PixieConfig {
  readonly root: string;
  readonly datasetDir: string;
  readonly rateLimits: RateLimitConfig | null;
  readonly traceOutput: string | null;
  readonly tracingEnabled: boolean;
}

function isTruthyEnv(value: string): boolean {
  return TRUE_ENV_VALUES.has(value.trim().toLowerCase());
}

function getFloatEnv(name: string, defaultValue: number): number {
  const raw = process.env[name];
  if (raw === undefined) return defaultValue;
  const parsed = parseFloat(raw);
  return isNaN(parsed) ? defaultValue : parsed;
}

function getRateLimitConfig(): RateLimitConfig | null {
  const enabledValue = process.env["PIXIE_RATE_LIMIT_ENABLED"];
  const hasOverrides =
    process.env["PIXIE_RATE_LIMIT_RPS"] !== undefined ||
    process.env["PIXIE_RATE_LIMIT_RPM"] !== undefined ||
    process.env["PIXIE_RATE_LIMIT_TPS"] !== undefined ||
    process.env["PIXIE_RATE_LIMIT_TPM"] !== undefined;

  if (enabledValue !== undefined && !isTruthyEnv(enabledValue)) return null;
  if (enabledValue === undefined && !hasOverrides) return null;

  return {
    rps: getFloatEnv("PIXIE_RATE_LIMIT_RPS", DEFAULT_RATE_LIMIT_RPS),
    rpm: getFloatEnv("PIXIE_RATE_LIMIT_RPM", DEFAULT_RATE_LIMIT_RPM),
    tps: getFloatEnv("PIXIE_RATE_LIMIT_TPS", DEFAULT_RATE_LIMIT_TPS),
    tpm: getFloatEnv("PIXIE_RATE_LIMIT_TPM", DEFAULT_RATE_LIMIT_TPM),
  };
}

/**
 * Read configuration from environment variables with defaults.
 *
 * Supported variables: PIXIE_ROOT, PIXIE_DATASET_DIR, PIXIE_RATE_LIMIT_*,
 * PIXIE_TRACE_OUTPUT, PIXIE_TRACING
 */
export function getConfig(): PixieConfig {
  loadDotenv();

  const root = process.env["PIXIE_ROOT"] ?? DEFAULT_ROOT;
  return {
    root,
    datasetDir: process.env["PIXIE_DATASET_DIR"] ?? path.join(root, "datasets"),
    rateLimits: getRateLimitConfig(),
    traceOutput: process.env["PIXIE_TRACE_OUTPUT"] ?? null,
    tracingEnabled: isTruthyEnv(process.env["PIXIE_TRACING"] ?? ""),
  };
}
