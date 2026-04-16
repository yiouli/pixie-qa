/**
 * Evaluation primitives: Evaluation result, Evaluator type, evaluate().
 */

import type { Evaluable } from "./evaluable.js";
import { collapseNamedData } from "./evaluable.js";
import { getRateLimiter } from "./rateLimiter.js";

/** The result of a single evaluator applied to a single test case. */
export interface Evaluation {
  readonly score: number;
  readonly reasoning: string;
  readonly details: Record<string, unknown>;
}

/**
 * An evaluator is any async callable that takes an Evaluable and returns an Evaluation.
 */
export type Evaluator = (
  evaluable: Evaluable,
  ...args: unknown[]
) => Promise<Evaluation>;

/**
 * Run a single evaluator against a single evaluable.
 *
 * - Rate-limits if configured
 * - Clamps returned score to [0.0, 1.0]
 * - Propagates evaluator exceptions unchanged
 */
export async function evaluate(
  evaluator: Evaluator,
  evaluable: Evaluable,
): Promise<Evaluation> {
  const limiter = getRateLimiter();
  if (limiter) {
    const inputStr = String(collapseNamedData(evaluable.evalInput));
    const outputStr = String(collapseNamedData(evaluable.evalOutput) ?? "");
    const estimatedTokens = limiter.estimateTokens(inputStr + outputStr);
    await limiter.acquire(estimatedTokens);
  }

  const result = await evaluator(evaluable);

  let clampedScore = result.score;
  if (clampedScore > 1.0) {
    console.warn(
      `Evaluator returned score ${clampedScore.toFixed(2)} > 1.0, clamping.`,
    );
    clampedScore = 1.0;
  } else if (clampedScore < 0.0) {
    console.warn(
      `Evaluator returned score ${clampedScore.toFixed(2)} < 0.0, clamping.`,
    );
    clampedScore = 0.0;
  }

  if (clampedScore !== result.score) {
    return {
      score: clampedScore,
      reasoning: result.reasoning,
      details: result.details,
    };
  }
  return result;
}
