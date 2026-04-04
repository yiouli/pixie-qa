"use strict";
/**
 * Autoevals adapters — pre-made evaluators wrapping `autoevals` scorers.
 *
 * Provides `AutoevalsAdapter`, which bridges the autoevals `Scorer`
 * interface to pixie's `Evaluator` protocol, and a set of factory
 * functions for common evaluation tasks.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.AutoevalsAdapter = void 0;
exports.LevenshteinMatch = LevenshteinMatch;
exports.ExactMatch = ExactMatch;
exports.NumericDiff = NumericDiff;
exports.JSONDiff = JSONDiff;
exports.ValidJSON = ValidJSON;
exports.ListContains = ListContains;
exports.EmbeddingSimilarity = EmbeddingSimilarity;
exports.Factuality = Factuality;
exports.ClosedQA = ClosedQA;
exports.Battle = Battle;
exports.Humor = Humor;
exports.Security = Security;
exports.Sql = Sql;
exports.Summary = Summary;
exports.Translation = Translation;
exports.Possible = Possible;
exports.Moderation = Moderation;
exports.ContextRelevancy = ContextRelevancy;
exports.Faithfulness = Faithfulness;
exports.AnswerRelevancy = AnswerRelevancy;
exports.AnswerCorrectness = AnswerCorrectness;
const evaluable_1 = require("../storage/evaluable");
/** Sentinel for "not provided". */
const _UNSET = Symbol("_UNSET_SCORER");
// ── Score → Evaluation conversion ────────────────────────────────────────────
function scoreToEvaluation(score) {
    const numeric = score.score !== null && score.score !== undefined
        ? Number(score.score)
        : 0.0;
    const metadata = score.metadata
        ? { ...score.metadata }
        : {};
    metadata["scorer_name"] = score.name;
    let reasoning;
    const rationale = metadata["rationale"];
    if (rationale &&
        typeof rationale === "string" &&
        rationale.trim().length > 0) {
        reasoning = rationale;
    }
    else if (score.score === null || score.score === undefined) {
        reasoning = "Evaluation skipped (score is null)";
    }
    else {
        reasoning = `${score.name}: ${score.score}`;
    }
    return { score: numeric, reasoning, details: metadata };
}
// ── AutoevalsAdapter ─────────────────────────────────────────────────────────
/**
 * Wraps an autoevals `Scorer` to satisfy the pixie `Evaluator` protocol.
 */
class AutoevalsAdapter {
    _scorer;
    _expected;
    _expectedKey;
    _inputKey;
    _extraMetadataKeys;
    _scorerKwargs;
    constructor(scorer, opts) {
        this._scorer = scorer;
        this._expected = opts?.expected ?? _UNSET;
        this._expectedKey = opts?.expectedKey ?? "expected";
        this._inputKey = opts?.inputKey === undefined ? "input" : opts.inputKey;
        this._extraMetadataKeys = opts?.extraMetadataKeys ?? [];
        this._scorerKwargs = opts?.scorerKwargs ?? {};
    }
    /** Return the underlying scorer's display name. */
    get name() {
        if (typeof this._scorer?.name === "string") {
            return this._scorer.name;
        }
        return this._scorer?.constructor?.name ?? "UnknownScorer";
    }
    /**
     * Run the wrapped scorer and return a pixie Evaluation.
     */
    async __call__(evaluable, _opts) {
        try {
            const output = evaluable.evalOutput;
            // Resolve expected — evaluable > constructor > metadata
            let expected;
            if (evaluable.expectedOutput !== evaluable_1.UNSET) {
                expected = evaluable.expectedOutput;
            }
            else if (this._expected !== _UNSET) {
                expected = this._expected;
            }
            else if (evaluable.evalMetadata !== null) {
                expected = evaluable.evalMetadata[this._expectedKey];
            }
            else {
                expected = null;
            }
            // Build kwargs
            const kwargs = {};
            if (this._inputKey !== null) {
                kwargs[this._inputKey] = evaluable.evalInput;
            }
            if (evaluable.evalMetadata !== null) {
                for (const key of this._extraMetadataKeys) {
                    if (key in evaluable.evalMetadata) {
                        kwargs[key] = evaluable.evalMetadata[key];
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
        }
        catch (exc) {
            const error = exc;
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
exports.AutoevalsAdapter = AutoevalsAdapter;
// ── Pre-made evaluator factories — Heuristic ─────────────────────────────────
function LevenshteinMatch() {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { Levenshtein } = require("autoevals");
    return new AutoevalsAdapter(new Levenshtein(), { inputKey: null });
}
function ExactMatch() {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const autoevals = require("autoevals");
    return new AutoevalsAdapter(new autoevals.ExactMatch(), { inputKey: null });
}
function NumericDiff() {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const autoevals = require("autoevals");
    return new AutoevalsAdapter(new autoevals.NumericDiff(), { inputKey: null });
}
function JSONDiff(opts) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const autoevals = require("autoevals");
    const scorerKwargs = {};
    if (opts?.stringScorer !== undefined) {
        scorerKwargs["string_scorer"] = opts.stringScorer;
    }
    return new AutoevalsAdapter(new autoevals.JSONDiff(scorerKwargs), {
        inputKey: null,
    });
}
function ValidJSON(opts) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const autoevals = require("autoevals");
    const scorerKwargs = {};
    if (opts?.schema !== undefined) {
        scorerKwargs["schema"] = opts.schema;
    }
    return new AutoevalsAdapter(new autoevals.ValidJSON(scorerKwargs), {
        inputKey: null,
    });
}
function ListContains(opts) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const autoevals = require("autoevals");
    const scorerKwargs = {};
    if (opts?.pairwiseScorer !== undefined) {
        scorerKwargs["pairwise_scorer"] = opts.pairwiseScorer;
    }
    scorerKwargs["allow_extra_entities"] = opts?.allowExtraEntities ?? false;
    return new AutoevalsAdapter(new autoevals.ListContains(scorerKwargs), {
        inputKey: null,
    });
}
// ── Pre-made evaluator factories — Embedding ─────────────────────────────────
function EmbeddingSimilarity(opts) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const autoevals = require("autoevals");
    const scorerKwargs = {};
    if (opts?.prefix !== undefined)
        scorerKwargs["prefix"] = opts.prefix;
    if (opts?.model !== undefined)
        scorerKwargs["model"] = opts.model;
    if (opts?.client !== undefined)
        scorerKwargs["client"] = opts.client;
    return new AutoevalsAdapter(new autoevals.EmbeddingSimilarity(scorerKwargs), { inputKey: null });
}
// ── Pre-made evaluator factories — LLM-as-judge ──────────────────────────────
function Factuality(opts) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const autoevals = require("autoevals");
    const scorerKwargs = {};
    if (opts?.model !== undefined)
        scorerKwargs["model"] = opts.model;
    if (opts?.client !== undefined)
        scorerKwargs["client"] = opts.client;
    return new AutoevalsAdapter(new autoevals.Factuality(scorerKwargs), {
        inputKey: "input",
    });
}
function ClosedQA(opts) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const autoevals = require("autoevals");
    const scorerKwargs = {};
    if (opts?.model !== undefined)
        scorerKwargs["model"] = opts.model;
    if (opts?.client !== undefined)
        scorerKwargs["client"] = opts.client;
    return new AutoevalsAdapter(new autoevals.ClosedQA(scorerKwargs), {
        inputKey: "input",
        extraMetadataKeys: ["criteria"],
    });
}
function Battle(opts) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const autoevals = require("autoevals");
    const scorerKwargs = {};
    if (opts?.model !== undefined)
        scorerKwargs["model"] = opts.model;
    if (opts?.client !== undefined)
        scorerKwargs["client"] = opts.client;
    return new AutoevalsAdapter(new autoevals.Battle(scorerKwargs), {
        inputKey: "instructions",
    });
}
function Humor(opts) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const autoevals = require("autoevals");
    const scorerKwargs = {};
    if (opts?.model !== undefined)
        scorerKwargs["model"] = opts.model;
    if (opts?.client !== undefined)
        scorerKwargs["client"] = opts.client;
    return new AutoevalsAdapter(new autoevals.Humor(scorerKwargs), {
        inputKey: null,
    });
}
function Security(opts) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const autoevals = require("autoevals");
    const scorerKwargs = {};
    if (opts?.model !== undefined)
        scorerKwargs["model"] = opts.model;
    if (opts?.client !== undefined)
        scorerKwargs["client"] = opts.client;
    return new AutoevalsAdapter(new autoevals.Security(scorerKwargs), {
        inputKey: "instructions",
    });
}
function Sql(opts) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const autoevals = require("autoevals");
    const scorerKwargs = {};
    if (opts?.model !== undefined)
        scorerKwargs["model"] = opts.model;
    if (opts?.client !== undefined)
        scorerKwargs["client"] = opts.client;
    return new AutoevalsAdapter(new autoevals.Sql(scorerKwargs), {
        inputKey: "input",
    });
}
function Summary(opts) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const autoevals = require("autoevals");
    const scorerKwargs = {};
    if (opts?.model !== undefined)
        scorerKwargs["model"] = opts.model;
    if (opts?.client !== undefined)
        scorerKwargs["client"] = opts.client;
    return new AutoevalsAdapter(new autoevals.Summary(scorerKwargs), {
        inputKey: "input",
    });
}
function Translation(opts) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const autoevals = require("autoevals");
    const ctorKwargs = {};
    if (opts?.model !== undefined)
        ctorKwargs["model"] = opts.model;
    if (opts?.client !== undefined)
        ctorKwargs["client"] = opts.client;
    const scorerKwargs = {};
    if (opts?.language !== undefined)
        scorerKwargs["language"] = opts.language;
    return new AutoevalsAdapter(new autoevals.Translation(ctorKwargs), {
        inputKey: "input",
        scorerKwargs,
    });
}
function Possible(opts) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const autoevals = require("autoevals");
    const scorerKwargs = {};
    if (opts?.model !== undefined)
        scorerKwargs["model"] = opts.model;
    if (opts?.client !== undefined)
        scorerKwargs["client"] = opts.client;
    return new AutoevalsAdapter(new autoevals.Possible(scorerKwargs), {
        inputKey: "input",
    });
}
// ── Pre-made evaluator factories — Moderation ────────────────────────────────
function Moderation(opts) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const autoevals = require("autoevals");
    const scorerKwargs = {};
    if (opts?.threshold !== undefined)
        scorerKwargs["threshold"] = opts.threshold;
    if (opts?.client !== undefined)
        scorerKwargs["client"] = opts.client;
    return new AutoevalsAdapter(new autoevals.Moderation(scorerKwargs), {
        inputKey: null,
    });
}
// ── Pre-made evaluator factories — RAGAS ──────────────────────────────────────
function ContextRelevancy(opts) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const autoevals = require("autoevals");
    const scorerKwargs = {};
    if (opts?.client !== undefined)
        scorerKwargs["client"] = opts.client;
    return new AutoevalsAdapter(new autoevals.ContextRelevancy(scorerKwargs), {
        inputKey: "input",
        extraMetadataKeys: ["context"],
    });
}
function Faithfulness(opts) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const autoevals = require("autoevals");
    const scorerKwargs = {};
    if (opts?.client !== undefined)
        scorerKwargs["client"] = opts.client;
    return new AutoevalsAdapter(new autoevals.Faithfulness(scorerKwargs), {
        inputKey: "input",
        extraMetadataKeys: ["context"],
    });
}
function AnswerRelevancy(opts) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const autoevals = require("autoevals");
    const scorerKwargs = {};
    if (opts?.client !== undefined)
        scorerKwargs["client"] = opts.client;
    return new AutoevalsAdapter(new autoevals.AnswerRelevancy(scorerKwargs), {
        inputKey: "input",
        extraMetadataKeys: ["context"],
    });
}
function AnswerCorrectness(opts) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const autoevals = require("autoevals");
    const scorerKwargs = {};
    if (opts?.client !== undefined)
        scorerKwargs["client"] = opts.client;
    return new AutoevalsAdapter(new autoevals.AnswerCorrectness(scorerKwargs), {
        inputKey: "input",
        extraMetadataKeys: ["context"],
    });
}
//# sourceMappingURL=scorers.js.map