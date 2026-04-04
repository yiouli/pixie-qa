"use strict";
/**
 * Central rate limiter for LLM evaluator calls.
 *
 * Controls throughput using configurable RPS, RPM, TPS, and TPM limits.
 * Uses sliding-window approach. The module exposes a singleton via
 * `getRateLimiter()`; when no configuration has been applied it returns
 * `null` and evaluator calls proceed without throttling.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.EvalRateLimiter = void 0;
exports.configureRateLimits = configureRateLimits;
exports.configureRateLimitsFromConfig = configureRateLimitsFromConfig;
exports.getRateLimiter = getRateLimiter;
exports._resetRateLimiter = _resetRateLimiter;
const config_1 = require("../config");
// ── EvalRateLimiter ──────────────────────────────────────────────────────────
class EvalRateLimiter {
    _config;
    /** Sliding-window records: [timestamp, tokenCount] */
    _secondWindow = [];
    _minuteWindow = [];
    constructor(config) {
        this._config = config;
    }
    get config() {
        return this._config;
    }
    /**
     * Estimate token count using `len(text) / 3` approximation.
     *
     * This is a rough heuristic — actual tokenization varies by model
     * and language. It intentionally over-counts to stay within limits.
     */
    estimateTokens(text) {
        return Math.floor(text.length / 3);
    }
    /**
     * Wait until the request can proceed within rate limits.
     *
     * Polls with a short interval until all four constraints
     * (RPS, RPM, TPS, TPM) are satisfied, then records the request.
     */
    async acquire(estimatedTokens = 0) {
        while (true) {
            const now = Date.now() / 1000; // seconds (monotonic-ish)
            this._evict(now);
            if (this._canProceed(now, estimatedTokens)) {
                this._record(now, estimatedTokens);
                return;
            }
            // Yield and retry
            await new Promise((resolve) => setTimeout(resolve, 50));
        }
    }
    _evict(now) {
        while (this._secondWindow.length > 0 &&
            now - this._secondWindow[0][0] >= 1.0) {
            this._secondWindow.shift();
        }
        while (this._minuteWindow.length > 0 &&
            now - this._minuteWindow[0][0] >= 60.0) {
            this._minuteWindow.shift();
        }
    }
    _canProceed(now, tokens) {
        const secCount = this._secondWindow.length;
        const secTokens = this._secondWindow.reduce((s, e) => s + e[1], 0);
        const minCount = this._minuteWindow.length;
        const minTokens = this._minuteWindow.reduce((s, e) => s + e[1], 0);
        if (secCount >= this._config.rps)
            return false;
        if (minCount >= this._config.rpm)
            return false;
        if (secTokens + tokens > this._config.tps)
            return false;
        return minTokens + tokens <= this._config.tpm;
    }
    _record(now, tokens) {
        this._secondWindow.push([now, tokens]);
        this._minuteWindow.push([now, tokens]);
    }
}
exports.EvalRateLimiter = EvalRateLimiter;
// ── Module-level singleton ───────────────────────────────────────────────────
let _rateLimiter = null;
let _rateLimiterInitialized = false;
/**
 * Set (or clear) the global rate limiter for evaluator calls.
 */
function configureRateLimits(config = null) {
    _rateLimiter = config === null ? null : new EvalRateLimiter(config);
    _rateLimiterInitialized = true;
}
/**
 * Apply the central Pixie config to the module-level rate limiter.
 */
function configureRateLimitsFromConfig(config) {
    const resolvedConfig = config ?? (0, config_1.getConfig)();
    configureRateLimits(resolvedConfig.rateLimits);
}
/**
 * Return the active rate limiter, auto-loading it from Pixie config once.
 */
function getRateLimiter() {
    if (!_rateLimiterInitialized) {
        configureRateLimitsFromConfig();
    }
    return _rateLimiter;
}
/** Reset the singleton. **Test-only.** @internal */
function _resetRateLimiter() {
    _rateLimiter = null;
    _rateLimiterInitialized = false;
}
//# sourceMappingURL=rateLimiter.js.map