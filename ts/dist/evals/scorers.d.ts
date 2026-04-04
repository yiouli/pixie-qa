/**
 * Autoevals adapters — pre-made evaluators wrapping `autoevals` scorers.
 *
 * Provides `AutoevalsAdapter`, which bridges the autoevals `Scorer`
 * interface to pixie's `Evaluator` protocol, and a set of factory
 * functions for common evaluation tasks.
 */
import type { Evaluable } from "../storage/evaluable";
import type { ObservationNode } from "../storage/tree";
import type { Evaluation } from "./evaluation";
type AnyScorer = any;
/**
 * Wraps an autoevals `Scorer` to satisfy the pixie `Evaluator` protocol.
 */
export declare class AutoevalsAdapter {
    private _scorer;
    private _expected;
    private _expectedKey;
    private _inputKey;
    private _extraMetadataKeys;
    private _scorerKwargs;
    constructor(scorer: AnyScorer, opts?: {
        expected?: unknown;
        expectedKey?: string;
        inputKey?: string | null;
        extraMetadataKeys?: readonly string[];
        scorerKwargs?: Record<string, unknown>;
    });
    /** Return the underlying scorer's display name. */
    get name(): string;
    /**
     * Run the wrapped scorer and return a pixie Evaluation.
     */
    __call__(evaluable: Evaluable, _opts?: {
        trace?: ObservationNode[];
    }): Promise<Evaluation>;
}
export declare function LevenshteinMatch(): AutoevalsAdapter;
export declare function ExactMatch(): AutoevalsAdapter;
export declare function NumericDiff(): AutoevalsAdapter;
export declare function JSONDiff(opts?: {
    stringScorer?: unknown;
}): AutoevalsAdapter;
export declare function ValidJSON(opts?: {
    schema?: unknown;
}): AutoevalsAdapter;
export declare function ListContains(opts?: {
    pairwiseScorer?: unknown;
    allowExtraEntities?: boolean;
}): AutoevalsAdapter;
export declare function EmbeddingSimilarity(opts?: {
    prefix?: string;
    model?: string;
    client?: unknown;
}): AutoevalsAdapter;
export declare function Factuality(opts?: {
    model?: string;
    client?: unknown;
}): AutoevalsAdapter;
export declare function ClosedQA(opts?: {
    model?: string;
    client?: unknown;
}): AutoevalsAdapter;
export declare function Battle(opts?: {
    model?: string;
    client?: unknown;
}): AutoevalsAdapter;
export declare function Humor(opts?: {
    model?: string;
    client?: unknown;
}): AutoevalsAdapter;
export declare function Security(opts?: {
    model?: string;
    client?: unknown;
}): AutoevalsAdapter;
export declare function Sql(opts?: {
    model?: string;
    client?: unknown;
}): AutoevalsAdapter;
export declare function Summary(opts?: {
    model?: string;
    client?: unknown;
}): AutoevalsAdapter;
export declare function Translation(opts?: {
    language?: string;
    model?: string;
    client?: unknown;
}): AutoevalsAdapter;
export declare function Possible(opts?: {
    model?: string;
    client?: unknown;
}): AutoevalsAdapter;
export declare function Moderation(opts?: {
    threshold?: number;
    client?: unknown;
}): AutoevalsAdapter;
export declare function ContextRelevancy(opts?: {
    client?: unknown;
}): AutoevalsAdapter;
export declare function Faithfulness(opts?: {
    client?: unknown;
}): AutoevalsAdapter;
export declare function AnswerRelevancy(opts?: {
    client?: unknown;
}): AutoevalsAdapter;
export declare function AnswerCorrectness(opts?: {
    client?: unknown;
}): AutoevalsAdapter;
export {};
//# sourceMappingURL=scorers.d.ts.map