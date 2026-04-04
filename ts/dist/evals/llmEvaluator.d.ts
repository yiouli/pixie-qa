/**
 * Factory for custom LLM-as-judge evaluators from prompt templates.
 *
 * Usage:
 *   import { createLlmEvaluator } from "./llmEvaluator";
 *
 *   const conciseVoiceStyle = createLlmEvaluator({
 *     name: "ConciseVoiceStyle",
 *     promptTemplate: `
 *       You are evaluating whether a voice agent response is concise.
 *       User said: {eval_input}
 *       Agent responded: {eval_output}
 *       Expected behavior: {expected_output}
 *       Score 1.0 if concise, 0.0 if verbose.
 *     `,
 *   });
 */
import OpenAI from "openai";
import type { Evaluable } from "../storage/evaluable";
import type { ObservationNode } from "../storage/tree";
import type { Evaluation } from "./evaluation";
declare class LLMEvaluator {
    private _name;
    private _promptTemplate;
    private _model;
    private _client;
    constructor(name: string, promptTemplate: string, model: string, client: OpenAI | null);
    get name(): string;
    private _getClient;
    private _renderPrompt;
    /** Run the LLM judge and parse the score. */
    __call__(evaluable: Evaluable, _opts?: {
        trace?: ObservationNode[];
    }): Promise<Evaluation>;
}
/**
 * Create a custom LLM-as-judge evaluator from a prompt template.
 *
 * Template variables (populated from the Evaluable fields):
 * - `{eval_input}` — the evaluable's input
 * - `{eval_output}` — the evaluable's output
 * - `{expected_output}` — the evaluable's expected output
 *
 * @throws if the template uses nested field access like `{eval_input[key]}`.
 */
export declare function createLlmEvaluator(opts: {
    name: string;
    promptTemplate: string;
    model?: string;
    client?: OpenAI | null;
}): LLMEvaluator;
export {};
//# sourceMappingURL=llmEvaluator.d.ts.map