/**
 * Central rate limiter for LLM evaluator calls.
 *
 * Controls throughput using configurable RPS, RPM, TPS, and TPM limits.
 * Uses sliding-window approach. The module exposes a singleton via
 * `getRateLimiter()`; when no configuration has been applied it returns
 * `null` and evaluator calls proceed without throttling.
 */

import type { PixieConfig, RateLimitConfig } from "../config";
import { getConfig } from "../config";

// ── EvalRateLimiter ──────────────────────────────────────────────────────────

export class EvalRateLimiter {
  private _config: RateLimitConfig;
  /** Sliding-window records: [timestamp, tokenCount] */
  private _secondWindow: Array<[number, number]> = [];
  private _minuteWindow: Array<[number, number]> = [];

  constructor(config: RateLimitConfig) {
    this._config = config;
  }

  get config(): RateLimitConfig {
    return this._config;
  }

  /** Estimate token count using `len(text) / 3` approximation. */
  estimateTokens(text: string): number {
    return Math.floor(text.length / 3);
  }

  /**
   * Wait until the request can proceed within rate limits.
   *
   * Polls with a short interval until all four constraints
   * (RPS, RPM, TPS, TPM) are satisfied, then records the request.
   */
  async acquire(estimatedTokens: number = 0): Promise<void> {
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

  private _evict(now: number): void {
    while (
      this._secondWindow.length > 0 &&
      now - this._secondWindow[0][0] >= 1.0
    ) {
      this._secondWindow.shift();
    }
    while (
      this._minuteWindow.length > 0 &&
      now - this._minuteWindow[0][0] >= 60.0
    ) {
      this._minuteWindow.shift();
    }
  }

  private _canProceed(now: number, tokens: number): boolean {
    const secCount = this._secondWindow.length;
    const secTokens = this._secondWindow.reduce((s, e) => s + e[1], 0);
    const minCount = this._minuteWindow.length;
    const minTokens = this._minuteWindow.reduce((s, e) => s + e[1], 0);

    if (secCount >= this._config.rps) return false;
    if (minCount >= this._config.rpm) return false;
    if (secTokens + tokens > this._config.tps) return false;
    return minTokens + tokens <= this._config.tpm;
  }

  private _record(now: number, tokens: number): void {
    this._secondWindow.push([now, tokens]);
    this._minuteWindow.push([now, tokens]);
  }
}

// ── Module-level singleton ───────────────────────────────────────────────────

let _rateLimiter: EvalRateLimiter | null = null;
let _rateLimiterInitialized = false;

/**
 * Set (or clear) the global rate limiter for evaluator calls.
 */
export function configureRateLimits(
  config: RateLimitConfig | null = null
): void {
  _rateLimiter = config === null ? null : new EvalRateLimiter(config);
  _rateLimiterInitialized = true;
}

/**
 * Apply the central Pixie config to the module-level rate limiter.
 */
export function configureRateLimitsFromConfig(
  config?: PixieConfig
): void {
  const resolvedConfig = config ?? getConfig();
  configureRateLimits(resolvedConfig.rateLimits);
}

/**
 * Return the active rate limiter, auto-loading it from Pixie config once.
 */
export function getRateLimiter(): EvalRateLimiter | null {
  if (!_rateLimiterInitialized) {
    configureRateLimitsFromConfig();
  }
  return _rateLimiter;
}

/** Reset the singleton. **Test-only.** @internal */
export function _resetRateLimiter(): void {
  _rateLimiter = null;
  _rateLimiterInitialized = false;
}
