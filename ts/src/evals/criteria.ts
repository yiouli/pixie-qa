/**
 * Pre-made pass criteria for `assertPass`.
 *
 * Provides `ScoreThreshold`, a configurable criterion that checks
 * whether a sufficient fraction of test cases score above a threshold.
 */

import type { Evaluation } from "./evaluation";

/**
 * Criteria function type: receives results matrix, returns [passed, message].
 */
export type PassCriteria = (
  results: Evaluation[][]
) => [boolean, string];

/**
 * Pass criteria: `pct` fraction of inputs must score >= `threshold`
 * on all evaluators.
 */
export class ScoreThreshold {
  readonly threshold: number;
  readonly pct: number;

  constructor(threshold: number = 0.5, pct: number = 1.0) {
    this.threshold = threshold;
    this.pct = pct;
  }

  /**
   * Evaluate the results matrix and return `[passed, message]`.
   *
   * @param results - Shape `[inputs][evaluators]`.
   */
  __call__(results: Evaluation[][]): [boolean, string] {
    const totalInputs = results.length;
    let passingInputs = 0;
    for (const inputEvals of results) {
      const allPass = inputEvals.every((e) => e.score >= this.threshold);
      if (allPass) passingInputs++;
    }

    if (totalInputs > 0 && passingInputs / totalInputs >= this.pct) {
      const pctActual = (passingInputs / totalInputs) * 100;
      return [
        true,
        `Pass: ${passingInputs}/${totalInputs} inputs (${pctActual.toFixed(1)}%) ` +
          `scored >= ${this.threshold} on all evaluators ` +
          `(required: ${(this.pct * 100).toFixed(1)}%)`,
      ];
    }

    const pctBest =
      totalInputs > 0 ? (passingInputs / totalInputs) * 100 : 0;
    return [
      false,
      `Fail: ${passingInputs}/${totalInputs} inputs (${pctBest.toFixed(1)}%) ` +
        `scored >= ${this.threshold} on all evaluators ` +
        `(required: ${(this.pct * 100).toFixed(1)}%)`,
    ];
  }
}
