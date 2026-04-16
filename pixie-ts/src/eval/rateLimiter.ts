/**
 * Central rate limiter for LLM evaluator calls.
 *
 * Controls throughput using configurable RPS, RPM, TPS, and TPM limits.
 */

import type { PixieConfig, RateLimitConfig } from "../config.js";
import { getConfig } from "../config.js";

/**
 * Sliding-window rate limiter for LLM evaluator calls.
 */
export class EvalRateLimiter {
  private readonly _config: RateLimitConfig;
  private readonly _secondWindow: Array<{ ts: number; tokens: number }> = [];
  private readonly _minuteWindow: Array<{ ts: number; tokens: number }> = [];

  constructor(config: RateLimitConfig) {
    this._config = config;
  }

  get config(): RateLimitConfig {
    return this._config;
  }

  /** Estimate token count using len/3 approximation. */
  estimateTokens(text: string): number {
    return Math.floor(text.length / 3);
  }

  /** Wait until the request can proceed within rate limits. */
  async acquire(estimatedTokens: number = 0): Promise<void> {
    while (true) {
      const now = performance.now() / 1000;
      this.evict(now);

      if (this.canProceed(now, estimatedTokens)) {
        this.record(now, estimatedTokens);
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
  }

  private evict(now: number): void {
    while (
      this._secondWindow.length > 0 &&
      now - this._secondWindow[0].ts >= 1.0
    ) {
      this._secondWindow.shift();
    }
    while (
      this._minuteWindow.length > 0 &&
      now - this._minuteWindow[0].ts >= 60.0
    ) {
      this._minuteWindow.shift();
    }
  }

  private canProceed(now: number, tokens: number): boolean {
    void now;
    const secCount = this._secondWindow.length;
    const secTokens = this._secondWindow.reduce((sum, e) => sum + e.tokens, 0);
    const minCount = this._minuteWindow.length;
    const minTokens = this._minuteWindow.reduce((sum, e) => sum + e.tokens, 0);

    if (secCount >= this._config.rps) return false;
    if (minCount >= this._config.rpm) return false;
    if (secTokens + tokens > this._config.tps) return false;
    return minTokens + tokens <= this._config.tpm;
  }

  private record(now: number, tokens: number): void {
    this._secondWindow.push({ ts: now, tokens });
    this._minuteWindow.push({ ts: now, tokens });
  }
}

// Module-level singleton
let _rateLimiter: EvalRateLimiter | null = null;
let _rateLimiterInitialized = false;

/**
 * Set (or clear) the global rate limiter for evaluator calls.
 */
export function configureRateLimits(
  config: RateLimitConfig | null = null,
): void {
  _rateLimiter = config ? new EvalRateLimiter(config) : null;
  _rateLimiterInitialized = true;
}

/**
 * Apply the central Pixie config to the module-level rate limiter.
 */
export function configureRateLimitsFromConfig(
  config?: PixieConfig | null,
): void {
  const resolvedConfig = config ?? getConfig();
  configureRateLimits(resolvedConfig.rateLimits);
}

/**
 * Return the active rate limiter, auto-loading from Pixie config once.
 */
export function getRateLimiter(): EvalRateLimiter | null {
  if (!_rateLimiterInitialized) {
    configureRateLimitsFromConfig();
  }
  return _rateLimiter;
}
