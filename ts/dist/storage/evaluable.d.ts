/**
 * Evaluable model and span-to-evaluable conversion.
 *
 * `Evaluable` is an immutable interface that serves as the uniform
 * data carrier for evaluators. The `UNSET` sentinel distinguishes
 * "expected output was never provided" from "expected output is
 * explicitly null/undefined".
 */
import type { LLMSpan, ObserveSpan } from "../instrumentation/spans";
/**
 * Any value that can be represented in JSON.
 */
export type JsonValue = string | number | boolean | null | JsonValue[] | {
    [key: string]: JsonValue;
};
/**
 * Sentinel to distinguish "not provided" from `null` / `undefined`.
 */
export declare const UNSET: unique symbol;
export type Unset = typeof UNSET;
/**
 * Uniform data carrier for evaluators.
 *
 * All fields use `JsonValue` to guarantee JSON round-trip fidelity.
 * `expectedOutput` uses a union with the `UNSET` sentinel so callers
 * can distinguish "expected output was not provided" from "expected
 * output is explicitly null".
 */
export interface Evaluable {
    readonly evalInput: JsonValue;
    readonly evalOutput: JsonValue;
    readonly evalMetadata: Record<string, JsonValue> | null;
    readonly expectedOutput: JsonValue | Unset;
    readonly evaluators: readonly string[] | null;
    readonly description: string | null;
}
/**
 * Build an `Evaluable` from a span.
 *
 * `expectedOutput` is left as `UNSET` — span data never carries
 * expected values.
 */
export declare function asEvaluable(span: ObserveSpan | LLMSpan): Evaluable;
//# sourceMappingURL=evaluable.d.ts.map