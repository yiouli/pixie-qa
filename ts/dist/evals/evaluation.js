"use strict";
/**
 * Evaluation primitives: Evaluation result, Evaluator type, evaluate().
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.createEvaluation = createEvaluation;
exports.evaluate = evaluate;
/**
 * Create an Evaluation with default empty details.
 */
function createEvaluation(opts) {
    return {
        score: opts.score,
        reasoning: opts.reasoning,
        details: opts.details ?? {},
    };
}
// ── evaluate() ───────────────────────────────────────────────────────────────
function isAsyncFunction(fn) {
    if (typeof fn !== "function")
        return false;
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
async function evaluate(evaluator, evaluable, opts) {
    const extraOpts = { trace: opts?.trace };
    // Rate-limit LLM evaluator calls when a limiter is configured
    const { getRateLimiter } = await Promise.resolve().then(() => __importStar(require("./rateLimiter")));
    const limiter = getRateLimiter();
    if (limiter) {
        const text = String(evaluable.evalInput ?? "") + String(evaluable.evalOutput ?? "");
        const estimatedTokens = limiter.estimateTokens(text);
        await limiter.acquire(estimatedTokens);
    }
    let result;
    if (isAsyncFunction(evaluator)) {
        result = await evaluator(evaluable, extraOpts);
    }
    else {
        result = await Promise.resolve(evaluator(evaluable, extraOpts));
    }
    // Clamp score to [0.0, 1.0]
    let clampedScore = result.score;
    if (clampedScore > 1.0)
        clampedScore = 1.0;
    else if (clampedScore < 0.0)
        clampedScore = 0.0;
    if (clampedScore !== result.score) {
        return {
            score: clampedScore,
            reasoning: result.reasoning,
            details: result.details,
        };
    }
    return result;
}
//# sourceMappingURL=evaluation.js.map