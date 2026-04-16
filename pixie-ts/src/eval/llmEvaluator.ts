/**
 * Factory for custom LLM-as-judge evaluators from prompt templates.
 */

import OpenAI from "openai";
import type { Evaluable } from "./evaluable.js";
import {
  collapseNamedData,
  type JsonValue,
  type Unset,
  UNSET,
} from "./evaluable.js";
import type { Evaluation } from "./evaluation.js";

const DEFAULT_MODEL = "gpt-4o-mini";

function valueToStr(value: JsonValue | Unset | null | undefined): string {
  if (value === null || value === undefined) return "";
  if (value === UNSET) return "(not provided)";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function serializeNamedData(
  items: { name: string; value: JsonValue }[],
): string {
  return valueToStr(collapseNamedData(items));
}

/**
 * Extract a 0-1 score and reasoning from LLM response text.
 */
function parseScore(text: string): [number, string] {
  // Try "Score: X" pattern
  let match = text.match(/[Ss]core\s*[:=]\s*([01](?:\.\d+)?)/);
  if (match) {
    const score = Math.min(Math.max(parseFloat(match[1]), 0.0), 1.0);
    return [score, text.trim()];
  }

  // Try "X/1" or "X/1.0"
  match = text.match(/([01](?:\.\d+)?)\s*\/\s*1(?:\.0)?/);
  if (match) {
    const score = Math.min(Math.max(parseFloat(match[1]), 0.0), 1.0);
    return [score, text.trim()];
  }

  // Try bare float on a line
  match = text.match(/^([01](?:\.\d+)?)\s*$/m);
  if (match) {
    const score = Math.min(Math.max(parseFloat(match[1]), 0.0), 1.0);
    return [score, text.trim()];
  }

  console.warn(
    `Could not parse score from LLM response: ${text.slice(0, 200)}`,
  );
  return [0.0, `Failed to parse score. Raw response: ${text.trim()}`];
}

class LlmEvaluator {
  private readonly _name: string;
  private readonly _promptTemplate: string;
  private readonly _model: string;
  private readonly _client: OpenAI | null;

  constructor(
    name: string,
    promptTemplate: string,
    model: string,
    client: OpenAI | null,
  ) {
    this._name = name;
    this._promptTemplate = promptTemplate;
    this._model = model;
    this._client = client;
  }

  get name(): string {
    return this._name;
  }

  private getClient(): OpenAI {
    return this._client ?? new OpenAI();
  }

  private renderPrompt(evaluable: Evaluable): string {
    let rendered = this._promptTemplate
      .replace(/\{eval_input\}/g, serializeNamedData(evaluable.evalInput))
      .replace(/\{eval_output\}/g, serializeNamedData(evaluable.evalOutput))
      .replace(/\{expectation\}/g, valueToStr(evaluable.expectation));
    return rendered + "\n\nRespond with 'Score: X.X' followed by reasoning.";
  }

  async evaluate(evaluable: Evaluable): Promise<Evaluation> {
    const prompt = this.renderPrompt(evaluable);
    const client = this.getClient();

    const response = await client.chat.completions.create({
      model: this._model,
      messages: [
        {
          role: "system",
          content:
            "You are an evaluation judge. Score the following on a scale of 0.0 to 1.0. Always include 'Score: X.X' in your response, followed by your reasoning.",
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

/**
 * Create a custom LLM-as-judge evaluator from a prompt template.
 *
 * Template variables: {eval_input}, {eval_output}, {expectation}
 */
export function createLlmEvaluator(
  name: string,
  promptTemplate: string,
  opts?: {
    model?: string;
    client?: OpenAI | null;
  },
): (evaluable: Evaluable) => Promise<Evaluation> {
  const evaluator = new LlmEvaluator(
    name,
    promptTemplate,
    opts?.model ?? DEFAULT_MODEL,
    opts?.client ?? null,
  );
  const fn = evaluator.evaluate.bind(evaluator);
  Object.defineProperty(fn, "name", { value: name });
  return fn;
}
