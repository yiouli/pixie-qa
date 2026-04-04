/**
 * Central rate limiter for LLM evaluator calls.
 *
 * Controls throughput using configurable RPS, RPM, TPS, and TPM limits.
 * Uses sliding-window approach. The module exposes a singleton via
 * `getRateLimiter()`; when no configuration has been applied it returns
 * `null` and evaluator calls proceed without throttling.
 */
import type { PixieConfig, RateLimitConfig } from "../config";
export declare class EvalRateLimiter {
    private _config;
    /** Sliding-window records: [timestamp, tokenCount] */
    private _secondWindow;
    private _minuteWindow;
    constructor(config: RateLimitConfig);
    get config(): RateLimitConfig;
    /**
     * Estimate token count using `len(text) / 3` approximation.
     *
     * This is a rough heuristic — actual tokenization varies by model
     * and language. It intentionally over-counts to stay within limits.
     */
    estimateTokens(text: string): number;
    /**
     * Wait until the request can proceed within rate limits.
     *
     * Polls with a short interval until all four constraints
     * (RPS, RPM, TPS, TPM) are satisfied, then records the request.
     */
    acquire(estimatedTokens?: number): Promise<void>;
    private _evict;
    private _canProceed;
    private _record;
}
/**
 * Set (or clear) the global rate limiter for evaluator calls.
 */
export declare function configureRateLimits(config?: RateLimitConfig | null): void;
/**
 * Apply the central Pixie config to the module-level rate limiter.
 */
export declare function configureRateLimitsFromConfig(config?: PixieConfig): void;
/**
 * Return the active rate limiter, auto-loading it from Pixie config once.
 */
export declare function getRateLimiter(): EvalRateLimiter | null;
/** Reset the singleton. **Test-only.** @internal */
export declare function _resetRateLimiter(): void;
//# sourceMappingURL=rateLimiter.d.ts.map