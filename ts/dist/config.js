"use strict";
/**
 * Centralized configuration with env var and `.env` overrides.
 *
 * All environment variables are prefixed with `PIXIE_`. `getConfig()` loads
 * the nearest `.env` from the current working directory at call time, while
 * preserving any variables already present in `process.env`. Values are
 * resolved at call time rather than import time so tests can safely
 * manipulate the process environment before calling `getConfig()`.
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_RATE_LIMIT_TPM = exports.DEFAULT_RATE_LIMIT_TPS = exports.DEFAULT_RATE_LIMIT_RPM = exports.DEFAULT_RATE_LIMIT_RPS = exports.DEFAULT_ROOT = void 0;
exports.getConfig = getConfig;
const dotenv_1 = __importDefault(require("dotenv"));
const path_1 = __importDefault(require("path"));
const fs_1 = __importDefault(require("fs"));
// ── Defaults ─────────────────────────────────────────────────────────────────
exports.DEFAULT_ROOT = "pixie_qa";
exports.DEFAULT_RATE_LIMIT_RPS = 4.0;
exports.DEFAULT_RATE_LIMIT_RPM = 50.0;
exports.DEFAULT_RATE_LIMIT_TPS = 10_000;
exports.DEFAULT_RATE_LIMIT_TPM = 500_000;
const TRUE_ENV_VALUES = new Set(["1", "true", "yes", "on"]);
// ── Helpers ──────────────────────────────────────────────────────────────────
function isTruthyEnv(value) {
    return TRUE_ENV_VALUES.has(value.trim().toLowerCase());
}
function getFloatEnv(name, defaultValue) {
    const raw = process.env[name];
    if (raw === undefined) {
        return defaultValue;
    }
    const parsed = parseFloat(raw);
    return Number.isNaN(parsed) ? defaultValue : parsed;
}
function getRateLimitConfig() {
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
        rps: getFloatEnv("PIXIE_RATE_LIMIT_RPS", exports.DEFAULT_RATE_LIMIT_RPS),
        rpm: getFloatEnv("PIXIE_RATE_LIMIT_RPM", exports.DEFAULT_RATE_LIMIT_RPM),
        tps: getFloatEnv("PIXIE_RATE_LIMIT_TPS", exports.DEFAULT_RATE_LIMIT_TPS),
        tpm: getFloatEnv("PIXIE_RATE_LIMIT_TPM", exports.DEFAULT_RATE_LIMIT_TPM),
    };
}
/**
 * Find the nearest `.env` file starting from `cwd` and walking up.
 */
function findDotenv() {
    let dir = process.cwd();
    while (true) {
        const candidate = path_1.default.join(dir, ".env");
        if (fs_1.default.existsSync(candidate)) {
            return candidate;
        }
        const parent = path_1.default.dirname(dir);
        if (parent === dir)
            break;
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
function getConfig() {
    // Load .env without overriding existing env vars
    const envPath = findDotenv();
    if (envPath) {
        dotenv_1.default.config({ path: envPath, override: false });
    }
    const root = process.env["PIXIE_ROOT"] ?? exports.DEFAULT_ROOT;
    return {
        root,
        dbPath: process.env["PIXIE_DB_PATH"] ?? path_1.default.join(root, "observations.db"),
        dbEngine: process.env["PIXIE_DB_ENGINE"] ?? "sqlite",
        datasetDir: process.env["PIXIE_DATASET_DIR"] ?? path_1.default.join(root, "datasets"),
        rateLimits: getRateLimitConfig(),
    };
}
//# sourceMappingURL=config.js.map