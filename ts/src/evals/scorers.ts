/**
 * Autoevals adapters — pre-made evaluators wrapping `autoevals` scorers.
 *
 * Provides `AutoevalsAdapter`, which bridges the autoevals `Scorer`
 * interface to pixie's `Evaluator` protocol, and a set of factory
 * functions for common evaluation tasks.
 */

import type { Evaluable } from "../storage/evaluable";
import { UNSET } from "../storage/evaluable";
import type { ObservationNode } from "../storage/tree";
import type { Evaluation } from "./evaluation";

// ── Types for autoevals ──────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyScorer = any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyScore = any;

/** Sentinel for "not provided". */
const _UNSET: unique symbol = Symbol("_UNSET_SCORER");

// ── Score → Evaluation conversion ────────────────────────────────────────────

function scoreToEvaluation(score: AnyScore): Evaluation {
  const numeric: number =
    score.score !== null && score.score !== undefined
      ? Number(score.score)
      : 0.0;
  const metadata: Record<string, unknown> = score.metadata
    ? { ...score.metadata }
    : {};
  metadata["scorer_name"] = score.name;

  let reasoning: string;
  const rationale = metadata["rationale"];
  if (
    rationale &&
    typeof rationale === "string" &&
    rationale.trim().length > 0
  ) {
    reasoning = rationale;
  } else if (score.score === null || score.score === undefined) {
    reasoning = "Evaluation skipped (score is null)";
  } else {
    reasoning = `${score.name}: ${score.score}`;
  }

  return { score: numeric, reasoning, details: metadata };
}

// ── AutoevalsAdapter ─────────────────────────────────────────────────────────

/**
 * Wraps an autoevals `Scorer` to satisfy the pixie `Evaluator` protocol.
 */
export class AutoevalsAdapter {
  private _scorer: AnyScorer;
  private _expected: unknown;
  private _expectedKey: string;
  private _inputKey: string | null;
  private _extraMetadataKeys: readonly string[];
  private _scorerKwargs: Record<string, unknown>;

  constructor(
    scorer: AnyScorer,
    opts?: {
      expected?: unknown;
      expectedKey?: string;
      inputKey?: string | null;
      extraMetadataKeys?: readonly string[];
      scorerKwargs?: Record<string, unknown>;
    }
  ) {
    this._scorer = scorer;
    this._expected = opts?.expected ?? _UNSET;
    this._expectedKey = opts?.expectedKey ?? "expected";
    this._inputKey = opts?.inputKey === undefined ? "input" : opts.inputKey;
    this._extraMetadataKeys = opts?.extraMetadataKeys ?? [];
    this._scorerKwargs = opts?.scorerKwargs ?? {};
  }

  /** Return the underlying scorer's display name. */
  get name(): string {
    if (typeof this._scorer?.name === "string") {
      return this._scorer.name;
    }
    return this._scorer?.constructor?.name ?? "UnknownScorer";
  }

  /**
   * Run the wrapped scorer and return a pixie Evaluation.
   */
  async __call__(
    evaluable: Evaluable,
    _opts?: { trace?: ObservationNode[] }
  ): Promise<Evaluation> {
    try {
      const output = evaluable.evalOutput;

      // Resolve expected — evaluable > constructor > metadata
      let expected: unknown;
      if (evaluable.expectedOutput !== UNSET) {
        expected = evaluable.expectedOutput;
      } else if (this._expected !== _UNSET) {
        expected = this._expected;
      } else if (evaluable.evalMetadata !== null) {
        expected = (evaluable.evalMetadata as Record<string, unknown>)[
          this._expectedKey
        ];
      } else {
        expected = null;
      }

      // Build kwargs
      const kwargs: Record<string, unknown> = {};
      if (this._inputKey !== null) {
        kwargs[this._inputKey] = evaluable.evalInput;
      }
      if (evaluable.evalMetadata !== null) {
        for (const key of this._extraMetadataKeys) {
          if (key in evaluable.evalMetadata) {
            kwargs[key] = (
              evaluable.evalMetadata as Record<string, unknown>
            )[key];
          }
        }
      }
      Object.assign(kwargs, this._scorerKwargs);

      const score = await this._scorer.eval({
        output,
        expected,
        ...kwargs,
      });
      return scoreToEvaluation(score);
    } catch (exc) {
      const error = exc as Error;
      return {
        score: 0.0,
        reasoning: error.message ?? String(exc),
        details: {
          error: error.name ?? "Error",
          stack: error.stack ?? "",
        },
      };
    }
  }
}

// ── Pre-made evaluator factories — Heuristic ─────────────────────────────────

export function LevenshteinMatch(): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { Levenshtein } = require("autoevals");
  return new AutoevalsAdapter(new Levenshtein(), { inputKey: null });
}

export function ExactMatch(): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const autoevals = require("autoevals");
  return new AutoevalsAdapter(new autoevals.ExactMatch(), { inputKey: null });
}

export function NumericDiff(): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const autoevals = require("autoevals");
  return new AutoevalsAdapter(new autoevals.NumericDiff(), { inputKey: null });
}

export function JSONDiff(opts?: {
  stringScorer?: unknown;
}): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const autoevals = require("autoevals");
  const scorerKwargs: Record<string, unknown> = {};
  if (opts?.stringScorer !== undefined) {
    scorerKwargs["string_scorer"] = opts.stringScorer;
  }
  return new AutoevalsAdapter(new autoevals.JSONDiff(scorerKwargs), {
    inputKey: null,
  });
}

export function ValidJSON(opts?: {
  schema?: unknown;
}): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const autoevals = require("autoevals");
  const scorerKwargs: Record<string, unknown> = {};
  if (opts?.schema !== undefined) {
    scorerKwargs["schema"] = opts.schema;
  }
  return new AutoevalsAdapter(new autoevals.ValidJSON(scorerKwargs), {
    inputKey: null,
  });
}

export function ListContains(opts?: {
  pairwiseScorer?: unknown;
  allowExtraEntities?: boolean;
}): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const autoevals = require("autoevals");
  const scorerKwargs: Record<string, unknown> = {};
  if (opts?.pairwiseScorer !== undefined) {
    scorerKwargs["pairwise_scorer"] = opts.pairwiseScorer;
  }
  scorerKwargs["allow_extra_entities"] = opts?.allowExtraEntities ?? false;
  return new AutoevalsAdapter(new autoevals.ListContains(scorerKwargs), {
    inputKey: null,
  });
}

// ── Pre-made evaluator factories — Embedding ─────────────────────────────────

export function EmbeddingSimilarity(opts?: {
  prefix?: string;
  model?: string;
  client?: unknown;
}): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const autoevals = require("autoevals");
  const scorerKwargs: Record<string, unknown> = {};
  if (opts?.prefix !== undefined) scorerKwargs["prefix"] = opts.prefix;
  if (opts?.model !== undefined) scorerKwargs["model"] = opts.model;
  if (opts?.client !== undefined) scorerKwargs["client"] = opts.client;
  return new AutoevalsAdapter(
    new autoevals.EmbeddingSimilarity(scorerKwargs),
    { inputKey: null }
  );
}

// ── Pre-made evaluator factories — LLM-as-judge ──────────────────────────────

export function Factuality(opts?: {
  model?: string;
  client?: unknown;
}): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const autoevals = require("autoevals");
  const scorerKwargs: Record<string, unknown> = {};
  if (opts?.model !== undefined) scorerKwargs["model"] = opts.model;
  if (opts?.client !== undefined) scorerKwargs["client"] = opts.client;
  return new AutoevalsAdapter(new autoevals.Factuality(scorerKwargs), {
    inputKey: "input",
  });
}

export function ClosedQA(opts?: {
  model?: string;
  client?: unknown;
}): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const autoevals = require("autoevals");
  const scorerKwargs: Record<string, unknown> = {};
  if (opts?.model !== undefined) scorerKwargs["model"] = opts.model;
  if (opts?.client !== undefined) scorerKwargs["client"] = opts.client;
  return new AutoevalsAdapter(new autoevals.ClosedQA(scorerKwargs), {
    inputKey: "input",
    extraMetadataKeys: ["criteria"],
  });
}

export function Battle(opts?: {
  model?: string;
  client?: unknown;
}): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const autoevals = require("autoevals");
  const scorerKwargs: Record<string, unknown> = {};
  if (opts?.model !== undefined) scorerKwargs["model"] = opts.model;
  if (opts?.client !== undefined) scorerKwargs["client"] = opts.client;
  return new AutoevalsAdapter(new autoevals.Battle(scorerKwargs), {
    inputKey: "instructions",
  });
}

export function Humor(opts?: {
  model?: string;
  client?: unknown;
}): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const autoevals = require("autoevals");
  const scorerKwargs: Record<string, unknown> = {};
  if (opts?.model !== undefined) scorerKwargs["model"] = opts.model;
  if (opts?.client !== undefined) scorerKwargs["client"] = opts.client;
  return new AutoevalsAdapter(new autoevals.Humor(scorerKwargs), {
    inputKey: null,
  });
}

export function Security(opts?: {
  model?: string;
  client?: unknown;
}): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const autoevals = require("autoevals");
  const scorerKwargs: Record<string, unknown> = {};
  if (opts?.model !== undefined) scorerKwargs["model"] = opts.model;
  if (opts?.client !== undefined) scorerKwargs["client"] = opts.client;
  return new AutoevalsAdapter(new autoevals.Security(scorerKwargs), {
    inputKey: "instructions",
  });
}

export function Sql(opts?: {
  model?: string;
  client?: unknown;
}): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const autoevals = require("autoevals");
  const scorerKwargs: Record<string, unknown> = {};
  if (opts?.model !== undefined) scorerKwargs["model"] = opts.model;
  if (opts?.client !== undefined) scorerKwargs["client"] = opts.client;
  return new AutoevalsAdapter(new autoevals.Sql(scorerKwargs), {
    inputKey: "input",
  });
}

export function Summary(opts?: {
  model?: string;
  client?: unknown;
}): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const autoevals = require("autoevals");
  const scorerKwargs: Record<string, unknown> = {};
  if (opts?.model !== undefined) scorerKwargs["model"] = opts.model;
  if (opts?.client !== undefined) scorerKwargs["client"] = opts.client;
  return new AutoevalsAdapter(new autoevals.Summary(scorerKwargs), {
    inputKey: "input",
  });
}

export function Translation(opts?: {
  language?: string;
  model?: string;
  client?: unknown;
}): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const autoevals = require("autoevals");
  const ctorKwargs: Record<string, unknown> = {};
  if (opts?.model !== undefined) ctorKwargs["model"] = opts.model;
  if (opts?.client !== undefined) ctorKwargs["client"] = opts.client;
  const scorerKwargs: Record<string, unknown> = {};
  if (opts?.language !== undefined) scorerKwargs["language"] = opts.language;
  return new AutoevalsAdapter(new autoevals.Translation(ctorKwargs), {
    inputKey: "input",
    scorerKwargs,
  });
}

export function Possible(opts?: {
  model?: string;
  client?: unknown;
}): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const autoevals = require("autoevals");
  const scorerKwargs: Record<string, unknown> = {};
  if (opts?.model !== undefined) scorerKwargs["model"] = opts.model;
  if (opts?.client !== undefined) scorerKwargs["client"] = opts.client;
  return new AutoevalsAdapter(new autoevals.Possible(scorerKwargs), {
    inputKey: "input",
  });
}

// ── Pre-made evaluator factories — Moderation ────────────────────────────────

export function Moderation(opts?: {
  threshold?: number;
  client?: unknown;
}): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const autoevals = require("autoevals");
  const scorerKwargs: Record<string, unknown> = {};
  if (opts?.threshold !== undefined) scorerKwargs["threshold"] = opts.threshold;
  if (opts?.client !== undefined) scorerKwargs["client"] = opts.client;
  return new AutoevalsAdapter(new autoevals.Moderation(scorerKwargs), {
    inputKey: null,
  });
}

// ── Pre-made evaluator factories — RAGAS ──────────────────────────────────────

export function ContextRelevancy(opts?: {
  client?: unknown;
}): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const autoevals = require("autoevals");
  const scorerKwargs: Record<string, unknown> = {};
  if (opts?.client !== undefined) scorerKwargs["client"] = opts.client;
  return new AutoevalsAdapter(new autoevals.ContextRelevancy(scorerKwargs), {
    inputKey: "input",
    extraMetadataKeys: ["context"],
  });
}

export function Faithfulness(opts?: {
  client?: unknown;
}): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const autoevals = require("autoevals");
  const scorerKwargs: Record<string, unknown> = {};
  if (opts?.client !== undefined) scorerKwargs["client"] = opts.client;
  return new AutoevalsAdapter(new autoevals.Faithfulness(scorerKwargs), {
    inputKey: "input",
    extraMetadataKeys: ["context"],
  });
}

export function AnswerRelevancy(opts?: {
  client?: unknown;
}): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const autoevals = require("autoevals");
  const scorerKwargs: Record<string, unknown> = {};
  if (opts?.client !== undefined) scorerKwargs["client"] = opts.client;
  return new AutoevalsAdapter(new autoevals.AnswerRelevancy(scorerKwargs), {
    inputKey: "input",
    extraMetadataKeys: ["context"],
  });
}

export function AnswerCorrectness(opts?: {
  client?: unknown;
}): AutoevalsAdapter {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const autoevals = require("autoevals");
  const scorerKwargs: Record<string, unknown> = {};
  if (opts?.client !== undefined) scorerKwargs["client"] = opts.client;
  return new AutoevalsAdapter(new autoevals.AnswerCorrectness(scorerKwargs), {
    inputKey: "input",
    extraMetadataKeys: ["context"],
  });
}
