/**
 * Centralized configuration with env var and `.env` overrides.
 *
 * All environment variables are prefixed with `PIXIE_`. `getConfig()` loads
 * the nearest `.env` from the current working directory at call time, while
 * preserving any variables already present in `process.env`. Values are
 * resolved at call time rather than import time so tests can safely
 * manipulate the process environment before calling `getConfig()`.
 */
export declare const DEFAULT_ROOT = "pixie_qa";
export declare const DEFAULT_RATE_LIMIT_RPS = 4;
export declare const DEFAULT_RATE_LIMIT_RPM = 50;
export declare const DEFAULT_RATE_LIMIT_TPS = 10000;
export declare const DEFAULT_RATE_LIMIT_TPM = 500000;
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
export declare function getConfig(): PixieConfig;
//# sourceMappingURL=config.d.ts.map