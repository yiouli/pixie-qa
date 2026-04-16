/**
 * Factory for agent-deferred evaluators.
 *
 * An agent evaluator raises AgentEvaluationPending instead of returning
 * an Evaluation. The evaluation harness catches this and records a
 * PendingEvaluation in the entry result.
 */

import type { Evaluable } from "./evaluable.js";
import type { Evaluation } from "./evaluation.js";

/**
 * Error raised by agent evaluators to signal deferred grading.
 */
export class AgentEvaluationPending extends Error {
  public readonly evaluatorName: string;
  public readonly criteria: string;

  constructor(evaluatorName: string, criteria: string) {
    super(`Agent evaluation pending: ${evaluatorName}`);
    this.name = "AgentEvaluationPending";
    this.evaluatorName = evaluatorName;
    this.criteria = criteria;
  }
}

class AgentEvaluator {
  private readonly _name: string;
  private readonly _criteria: string;

  constructor(name: string, criteria: string) {
    this._name = name;
    this._criteria = criteria;
  }

  get name(): string {
    return this._name;
  }

  async __call__(evaluable: Evaluable): Promise<Evaluation> {
    void evaluable;
    throw new AgentEvaluationPending(this._name, this._criteria);
  }

  /** Make the instance callable. */
  get call(): (evaluable: Evaluable) => Promise<Evaluation> {
    return this.__call__.bind(this);
  }
}

/**
 * Create an evaluator whose grading is deferred to a coding agent.
 *
 * The returned evaluator satisfies the Evaluator interface but always
 * throws AgentEvaluationPending when called.
 */
export function createAgentEvaluator(
  name: string,
  criteria: string,
): (evaluable: Evaluable) => Promise<Evaluation> {
  const evaluator = new AgentEvaluator(name, criteria);
  const fn = evaluator.call;
  Object.defineProperty(fn, "name", { value: name });
  return fn;
}
