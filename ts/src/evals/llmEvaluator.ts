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
import { UNSET } from "../storage/evaluable";
import type { ObservationNode } from "../storage/tree";
import type { Evaluation } from "./evaluation";

// ── Constants ────────────────────────────────────────────────────────────────

const DEFAULT_MODEL = "gpt-4o-mini";

/** Regex to detect nested field access like `{eval_input[key]}` in templates. */
const NESTED_ACCESS_RE =
  /\{(eval_input|eval_output|expected_output)\[/;

// ── Helpers ──────────────────────────────────────────────────────────────────

function valueToStr(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (value === UNSET) return "(not provided)";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

/**
 * Extract a 0-1 score and reasoning from LLM response text.
 */
function parseScore(text: string): [number, string] {
  // Try "Score: X" pattern
  let match = text.match(/[Ss]core\s*[:=]\s*([01](?:\.\d+)?)/);
  if (match) {
    const score = Math.min(Math.max(parseFloat(match[1]), 0), 1);
    return [score, text.trim()];
  }

  // Try "X/1" or "X/1.0" pattern
  match = text.match(/([01](?:\.\d+)?)\s*\/\s*1(?:\.0)?/);
  if (match) {
    const score = Math.min(Math.max(parseFloat(match[1]), 0), 1);
    return [score, text.trim()];
  }

  // Try bare float on a line
  match = text.match(/^([01](?:\.\d+)?)\s*$/m);
  if (match) {
    const score = Math.min(Math.max(parseFloat(match[1]), 0), 1);
    return [score, text.trim()];
  }

  // Fallback: couldn't parse score
  return [0.0, `Failed to parse score. Raw response: ${text.trim()}`];
}

// ── LLMEvaluator class ───────────────────────────────────────────────────────

class LLMEvaluator {
  private _name: string;
  private _promptTemplate: string;
  private _model: string;
  private _client: OpenAI | null;

  constructor(
    name: string,
    promptTemplate: string,
    model: string,
    client: OpenAI | null
  ) {
    this._name = name;
    this._promptTemplate = promptTemplate;
    this._model = model;
    this._client = client;
  }

  get name(): string {
    return this._name;
  }

  private _getClient(): OpenAI {
    if (this._client !== null) return this._client;
    return new OpenAI();
  }

  private _renderPrompt(evaluable: Evaluable): string {
    const rendered = this._promptTemplate
      .replace(/\{eval_input\}/g, valueToStr(evaluable.evalInput))
      .replace(/\{eval_output\}/g, valueToStr(evaluable.evalOutput))
      .replace(
        /\{expected_output\}/g,
        valueToStr(evaluable.expectedOutput)
      );
    return rendered + "\n\nRespond with 'Score: X.X' followed by reasoning.";
  }

  /** Run the LLM judge and parse the score. */
  async __call__(
    evaluable: Evaluable,
    _opts?: { trace?: ObservationNode[] }
  ): Promise<Evaluation> {
    const prompt = this._renderPrompt(evaluable);
    const client = this._getClient();

    const response = await client.chat.completions.create({
      model: this._model,
      messages: [
        {
          role: "system",
          content:
            "You are an evaluation judge. Score the following on " +
            "a scale of 0.0 to 1.0. Always include 'Score: X.X' " +
            "in your response, followed by your reasoning.",
        },
        { role: "user", content: prompt },
      ],
      temperature: 0.0,
    });

    const text = response.choices[0]?.message?.content ?? "";
    const [score, reasoning] = parseScore(text);

    return {
      score,
      reasoning,
      details: { evaluator: this._name, model: this._model },
    };
  }
}

// ── Public factory ───────────────────────────────────────────────────────────

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
export function createLlmEvaluator(opts: {
  name: string;
  promptTemplate: string;
  model?: string;
  client?: OpenAI | null;
}): LLMEvaluator {
  const match = NESTED_ACCESS_RE.exec(opts.promptTemplate);
  if (match) {
    throw new Error(
      `Nested field access like '{${match[1]}[...]}' is not ` +
        `supported in prompt templates. Use '{${match[1]}}' ` +
        `instead — object values are serialized to JSON automatically.`
    );
  }
  return new LLMEvaluator(
    opts.name,
    opts.promptTemplate,
    opts.model ?? DEFAULT_MODEL,
    opts.client ?? null
  );
}
