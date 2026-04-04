/**
 * Evaluation primitives: Evaluation result, Evaluator type, evaluate().
 */

import type { Evaluable } from "../storage/evaluable";
import type { ObservationNode } from "../storage/tree";

// ── Evaluation ───────────────────────────────────────────────────────────────

/**
 * The result of a single evaluator applied to a single test case.
 */
export interface Evaluation {
  readonly score: number;
  readonly reasoning: string;
  readonly details: Record<string, unknown>;
}

/**
 * Create an Evaluation with default empty details.
 */
export function createEvaluation(opts: {
  score: number;
  reasoning: string;
  details?: Record<string, unknown>;
}): Evaluation {
  return {
    score: opts.score,
    reasoning: opts.reasoning,
    details: opts.details ?? {},
  };
}

// ── Evaluator type ───────────────────────────────────────────────────────────

/**
 * An evaluator is any callable matching this signature.
 *
 * Both sync and async functions are supported; sync evaluators are
 * wrapped automatically.
 */
export type Evaluator = (
  evaluable: Evaluable,
  opts?: { trace?: ObservationNode[] }
) => Evaluation | Promise<Evaluation>;

// ── evaluate() ───────────────────────────────────────────────────────────────

function isAsyncFunction(fn: unknown): boolean {
  if (typeof fn !== "function") return false;
  return fn.constructor.name === "AsyncFunction";
}

/**
 * Run a single evaluator against a single evaluable.
 *
 * - Calls evaluator with `evaluable` and optional `trace`.
 * - Clamps returned `score` to [0.0, 1.0].
 * - Applies rate limiting if configured.
 * - Evaluator errors propagate unchanged.
 */
export async function evaluate(
  evaluator: Evaluator,
  evaluable: Evaluable,
  opts?: { trace?: ObservationNode[] }
): Promise<Evaluation> {
  const extraOpts = { trace: opts?.trace };

  // Rate-limit LLM evaluator calls when a limiter is configured
  const { getRateLimiter } = await import("./rateLimiter");
  const limiter = getRateLimiter();
  if (limiter) {
    const text =
      String(evaluable.evalInput ?? "") + String(evaluable.evalOutput ?? "");
    const estimatedTokens = limiter.estimateTokens(text);
    await limiter.acquire(estimatedTokens);
  }

  let result: Evaluation;
  if (isAsyncFunction(evaluator)) {
    result = await evaluator(evaluable, extraOpts);
  } else {
    result = await Promise.resolve(evaluator(evaluable, extraOpts));
  }

  // Clamp score to [0.0, 1.0]
  let clampedScore = result.score;
  if (clampedScore > 1.0) clampedScore = 1.0;
  else if (clampedScore < 0.0) clampedScore = 0.0;

  if (clampedScore !== result.score) {
    return {
      score: clampedScore,
      reasoning: result.reasoning,
      details: result.details,
    };
  }
  return result;
}
