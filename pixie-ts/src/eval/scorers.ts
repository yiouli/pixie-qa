/**
 * Pre-built evaluator factories — TypeScript equivalents of autoevals adapters.
 *
 * Since the autoevals package doesn't have an official TS SDK with the same
 * scorers, we provide stub implementations that use the OpenAI API directly
 * for LLM-as-judge evaluators. Heuristic evaluators are implemented natively.
 */

import OpenAI from "openai";
import type { Evaluable } from "./evaluable.js";
import {
  collapseNamedData,
  UNSET,
  type JsonValue,
  type Unset,
} from "./evaluable.js";
import type { Evaluation } from "./evaluation.js";

type EvaluatorFn = (evaluable: Evaluable) => Promise<Evaluation>;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function resolveExpected(evaluable: Evaluable): JsonValue | null {
  if (evaluable.expectation !== null && evaluable.expectation !== UNSET) {
    return evaluable.expectation as JsonValue;
  }
  if (evaluable.evalMetadata) {
    return (evaluable.evalMetadata["expected"] as JsonValue) ?? null;
  }
  return null;
}

function toStr(value: JsonValue | null | undefined): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

// ---------------------------------------------------------------------------
// Heuristic scorers
// ---------------------------------------------------------------------------

function levenshteinDistance(a: string, b: string): number {
  const m = a.length;
  const n = b.length;
  const dp: number[][] = Array.from({ length: m + 1 }, () =>
    Array(n + 1).fill(0),
  );
  for (let i = 0; i <= m; i++) dp[i][0] = i;
  for (let j = 0; j <= n; j++) dp[0][j] = j;
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] =
        a[i - 1] === b[j - 1]
          ? dp[i - 1][j - 1]
          : 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);
    }
  }
  return dp[m][n];
}

/** Edit-distance string similarity evaluator. */
export function LevenshteinMatch(): EvaluatorFn {
  return async (evaluable: Evaluable): Promise<Evaluation> => {
    const output = toStr(collapseNamedData(evaluable.evalOutput));
    const expected = toStr(resolveExpected(evaluable));
    if (!output && !expected) {
      return { score: 1.0, reasoning: "Both empty", details: {} };
    }
    const maxLen = Math.max(output.length, expected.length);
    const distance = levenshteinDistance(output, expected);
    const score = maxLen === 0 ? 1.0 : 1.0 - distance / maxLen;
    return {
      score,
      reasoning: `Levenshtein similarity: ${score.toFixed(3)}`,
      details: { distance },
    };
  };
}

/** Exact value comparison evaluator. */
export function ExactMatch(): EvaluatorFn {
  return async (evaluable: Evaluable): Promise<Evaluation> => {
    const output = collapseNamedData(evaluable.evalOutput);
    const expected = resolveExpected(evaluable);
    const outputStr = JSON.stringify(output);
    const expectedStr = JSON.stringify(expected);
    const match = outputStr === expectedStr;
    return {
      score: match ? 1.0 : 0.0,
      reasoning: match ? "Exact match" : "No match",
      details: {},
    };
  };
}

/** Normalised numeric difference evaluator. */
export function NumericDiff(): EvaluatorFn {
  return async (evaluable: Evaluable): Promise<Evaluation> => {
    const output = Number(collapseNamedData(evaluable.evalOutput));
    const expected = Number(resolveExpected(evaluable));
    if (isNaN(output) || isNaN(expected)) {
      return { score: 0.0, reasoning: "Non-numeric values", details: {} };
    }
    const maxAbs = Math.max(Math.abs(output), Math.abs(expected), 1);
    const score = 1.0 - Math.abs(output - expected) / maxAbs;
    return {
      score: Math.max(0.0, score),
      reasoning: `Numeric diff: ${score.toFixed(3)}`,
      details: { output, expected },
    };
  };
}

/** Structural JSON comparison evaluator. */
export function JSONDiff(): EvaluatorFn {
  return async (evaluable: Evaluable): Promise<Evaluation> => {
    const output = collapseNamedData(evaluable.evalOutput);
    const expected = resolveExpected(evaluable);
    const outputStr = JSON.stringify(output, null, 0);
    const expectedStr = JSON.stringify(expected, null, 0);
    const match = outputStr === expectedStr;
    return {
      score: match ? 1.0 : 0.0,
      reasoning: match ? "JSON structures match" : "JSON structures differ",
      details: {},
    };
  };
}

/** JSON syntax and schema validation evaluator. */
export function ValidJSON(): EvaluatorFn {
  return async (evaluable: Evaluable): Promise<Evaluation> => {
    const output = collapseNamedData(evaluable.evalOutput);
    try {
      const str = typeof output === "string" ? output : JSON.stringify(output);
      JSON.parse(str);
      return { score: 1.0, reasoning: "Valid JSON", details: {} };
    } catch {
      return { score: 0.0, reasoning: "Invalid JSON", details: {} };
    }
  };
}

/** List overlap evaluator. */
export function ListContains(): EvaluatorFn {
  return async (evaluable: Evaluable): Promise<Evaluation> => {
    const output = collapseNamedData(evaluable.evalOutput);
    const expected = resolveExpected(evaluable);
    const outputArr = Array.isArray(output) ? output : [];
    const expectedArr = Array.isArray(expected) ? expected : [];
    if (expectedArr.length === 0) {
      return { score: 1.0, reasoning: "Empty expected list", details: {} };
    }
    const outputStrs = new Set(outputArr.map((x) => JSON.stringify(x)));
    const found = expectedArr.filter((x) =>
      outputStrs.has(JSON.stringify(x)),
    ).length;
    const score = found / expectedArr.length;
    return {
      score,
      reasoning: `Found ${found}/${expectedArr.length} expected items`,
      details: { found, total: expectedArr.length },
    };
  };
}

// ---------------------------------------------------------------------------
// LLM-as-judge evaluator helper
// ---------------------------------------------------------------------------

function createLlmJudge(
  name: string,
  systemPrompt: string,
  buildUserPrompt: (evaluable: Evaluable) => string,
  opts?: { model?: string; client?: OpenAI | null },
): EvaluatorFn {
  const model = opts?.model ?? "gpt-4o-mini";
  const getClient = () => opts?.client ?? new OpenAI();

  return async (evaluable: Evaluable): Promise<Evaluation> => {
    try {
      const client = getClient();
      const response = await client.chat.completions.create({
        model,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: buildUserPrompt(evaluable) },
        ],
        temperature: 0.0,
      });

      const text = response.choices[0]?.message?.content ?? "";
      const scoreMatch = text.match(/[Ss]core\s*[:=]\s*([01](?:\.\d+)?)/);
      const score = scoreMatch
        ? Math.min(Math.max(parseFloat(scoreMatch[1]), 0.0), 1.0)
        : 0.0;

      return {
        score,
        reasoning: text.trim(),
        details: { evaluator: name, model },
      };
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return {
        score: 0.0,
        reasoning: msg,
        details: { error: msg },
      };
    }
  };
}

// ---------------------------------------------------------------------------
// LLM-as-judge evaluators
// ---------------------------------------------------------------------------

/** Factual accuracy evaluator (LLM-as-judge). */
export function Factuality(opts?: {
  model?: string;
  client?: OpenAI | null;
}): EvaluatorFn {
  return createLlmJudge(
    "Factuality",
    "You are an evaluation judge. Score factual accuracy on 0.0-1.0. Always include 'Score: X.X'.",
    (e) => {
      const input = toStr(collapseNamedData(e.evalInput));
      const output = toStr(collapseNamedData(e.evalOutput));
      const expected = toStr(resolveExpected(e));
      return `Input: ${input}\nOutput: ${output}\nExpected: ${expected}\n\nIs the output factually consistent with the expected answer?`;
    },
    opts,
  );
}

/** Closed-book QA evaluator (LLM-as-judge). */
export function ClosedQA(opts?: {
  model?: string;
  client?: OpenAI | null;
}): EvaluatorFn {
  return createLlmJudge(
    "ClosedQA",
    "You are an evaluation judge. Score answer correctness on 0.0-1.0. Always include 'Score: X.X'.",
    (e) => {
      const input = toStr(collapseNamedData(e.evalInput));
      const output = toStr(collapseNamedData(e.evalOutput));
      const expected = toStr(resolveExpected(e));
      return `Question: ${input}\nAnswer: ${output}\nExpected: ${expected}\n\nDoes the answer correctly address the question?`;
    },
    opts,
  );
}

/** Battle comparison evaluator (LLM-as-judge). */
export function Battle(opts?: {
  model?: string;
  client?: OpenAI | null;
}): EvaluatorFn {
  return createLlmJudge(
    "Battle",
    "You are an evaluation judge comparing two outputs. Score on 0.0-1.0. Always include 'Score: X.X'.",
    (e) => {
      const output = toStr(collapseNamedData(e.evalOutput));
      const expected = toStr(resolveExpected(e));
      return `Output A: ${output}\nOutput B: ${expected}\n\nWhich output is better? Score 1.0 if A is much better, 0.5 if equal.`;
    },
    opts,
  );
}

/** Humor evaluator (LLM-as-judge). */
export function Humor(opts?: {
  model?: string;
  client?: OpenAI | null;
}): EvaluatorFn {
  return createLlmJudge(
    "Humor",
    "You are a humor evaluation judge. Score on 0.0-1.0. Always include 'Score: X.X'.",
    (e) => {
      const output = toStr(collapseNamedData(e.evalOutput));
      return `Text: ${output}\n\nHow funny is this text?`;
    },
    opts,
  );
}

/** Security evaluator (LLM-as-judge). */
export function Security(opts?: {
  model?: string;
  client?: OpenAI | null;
}): EvaluatorFn {
  return createLlmJudge(
    "Security",
    "You are a security evaluation judge. Score on 0.0-1.0. Always include 'Score: X.X'.",
    (e) => {
      const output = toStr(collapseNamedData(e.evalOutput));
      return `Output: ${output}\n\nDoes this output contain security vulnerabilities or leak sensitive information?`;
    },
    opts,
  );
}

/** SQL evaluator (LLM-as-judge). */
export function Sql(opts?: {
  model?: string;
  client?: OpenAI | null;
}): EvaluatorFn {
  return createLlmJudge(
    "Sql",
    "You are a SQL evaluation judge. Score on 0.0-1.0. Always include 'Score: X.X'.",
    (e) => {
      const output = toStr(collapseNamedData(e.evalOutput));
      const expected = toStr(resolveExpected(e));
      return `Generated SQL: ${output}\nExpected SQL: ${expected}\n\nDo these queries produce equivalent results?`;
    },
    opts,
  );
}

/** Summary evaluator (LLM-as-judge). */
export function Summary(opts?: {
  model?: string;
  client?: OpenAI | null;
}): EvaluatorFn {
  return createLlmJudge(
    "Summary",
    "You are a summary evaluation judge. Score on 0.0-1.0. Always include 'Score: X.X'.",
    (e) => {
      const input = toStr(collapseNamedData(e.evalInput));
      const output = toStr(collapseNamedData(e.evalOutput));
      return `Source: ${input}\nSummary: ${output}\n\nHow well does the summary capture the key points?`;
    },
    opts,
  );
}

/** Translation evaluator (LLM-as-judge). */
export function Translation(opts?: {
  language?: string;
  model?: string;
  client?: OpenAI | null;
}): EvaluatorFn {
  const lang = opts?.language ?? "the target language";
  return createLlmJudge(
    "Translation",
    `You are a translation evaluation judge for ${lang}. Score on 0.0-1.0. Always include 'Score: X.X'.`,
    (e) => {
      const input = toStr(collapseNamedData(e.evalInput));
      const output = toStr(collapseNamedData(e.evalOutput));
      const expected = toStr(resolveExpected(e));
      return `Source: ${input}\nTranslation: ${output}\nExpected: ${expected}\n\nHow accurate is the translation?`;
    },
    opts,
  );
}

/** Possibility evaluator (LLM-as-judge). */
export function Possible(opts?: {
  model?: string;
  client?: OpenAI | null;
}): EvaluatorFn {
  return createLlmJudge(
    "Possible",
    "You are an evaluation judge. Score on 0.0-1.0. Always include 'Score: X.X'.",
    (e) => {
      const input = toStr(collapseNamedData(e.evalInput));
      const output = toStr(collapseNamedData(e.evalOutput));
      return `Input: ${input}\nOutput: ${output}\n\nIs this output a possible/valid response?`;
    },
    opts,
  );
}

// ---------------------------------------------------------------------------
// Moderation
// ---------------------------------------------------------------------------

/** OpenAI content-moderation check. */
export function Moderation(opts?: {
  threshold?: number;
  client?: OpenAI | null;
}): EvaluatorFn {
  const threshold = opts?.threshold ?? 0.5;
  const getClient = () => opts?.client ?? new OpenAI();

  return async (evaluable: Evaluable): Promise<Evaluation> => {
    try {
      const client = getClient();
      const output = toStr(collapseNamedData(evaluable.evalOutput));
      const response = await client.moderations.create({ input: output });
      const result = response.results[0];
      const flagged = result?.flagged ?? false;
      return {
        score: flagged ? 0.0 : 1.0,
        reasoning: flagged
          ? `Content flagged by moderation (threshold: ${threshold})`
          : "Content passed moderation",
        details: { flagged, categories: result?.categories ?? {} },
      };
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return { score: 0.0, reasoning: msg, details: { error: msg } };
    }
  };
}

// ---------------------------------------------------------------------------
// Embedding
// ---------------------------------------------------------------------------

/** Embedding-based semantic similarity evaluator. */
export function EmbeddingSimilarity(opts?: {
  prefix?: string;
  model?: string;
  client?: OpenAI | null;
}): EvaluatorFn {
  const embModel = opts?.model ?? "text-embedding-3-small";
  const getClient = () => opts?.client ?? new OpenAI();

  return async (evaluable: Evaluable): Promise<Evaluation> => {
    try {
      const client = getClient();
      const output = toStr(collapseNamedData(evaluable.evalOutput));
      const expected = toStr(resolveExpected(evaluable));
      const prefix = opts?.prefix ? opts.prefix + " " : "";

      const [outEmb, expEmb] = await Promise.all([
        client.embeddings.create({
          model: embModel,
          input: prefix + output,
        }),
        client.embeddings.create({
          model: embModel,
          input: prefix + expected,
        }),
      ]);

      const vecA = outEmb.data[0].embedding;
      const vecB = expEmb.data[0].embedding;
      let dot = 0;
      let normA = 0;
      let normB = 0;
      for (let i = 0; i < vecA.length; i++) {
        dot += vecA[i] * vecB[i];
        normA += vecA[i] * vecA[i];
        normB += vecB[i] * vecB[i];
      }
      const similarity = dot / (Math.sqrt(normA) * Math.sqrt(normB));

      return {
        score: Math.max(0.0, Math.min(1.0, similarity)),
        reasoning: `Cosine similarity: ${similarity.toFixed(4)}`,
        details: { similarity, model: embModel },
      };
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return { score: 0.0, reasoning: msg, details: { error: msg } };
    }
  };
}

// ---------------------------------------------------------------------------
// RAGAS metrics (LLM-based approximations)
// ---------------------------------------------------------------------------

/** Context relevancy evaluator (RAGAS). */
export function ContextRelevancy(opts?: {
  client?: OpenAI | null;
}): EvaluatorFn {
  return createLlmJudge(
    "ContextRelevancy",
    "You are a RAGAS-style context relevancy judge. Score 0.0-1.0. Always include 'Score: X.X'.",
    (e) => {
      const input = toStr(collapseNamedData(e.evalInput));
      const context = e.evalMetadata?.["context"] ?? "";
      return `Question: ${input}\nContext: ${toStr(context as JsonValue)}\n\nHow relevant is the context to the question?`;
    },
    opts,
  );
}

/** Faithfulness evaluator (RAGAS). */
export function Faithfulness(opts?: { client?: OpenAI | null }): EvaluatorFn {
  return createLlmJudge(
    "Faithfulness",
    "You are a RAGAS-style faithfulness judge. Score 0.0-1.0. Always include 'Score: X.X'.",
    (e) => {
      const output = toStr(collapseNamedData(e.evalOutput));
      const context = e.evalMetadata?.["context"] ?? "";
      return `Answer: ${output}\nContext: ${toStr(context as JsonValue)}\n\nIs the answer faithful to the context (no hallucinations)?`;
    },
    opts,
  );
}

/** Answer relevancy evaluator (RAGAS). */
export function AnswerRelevancy(opts?: {
  client?: OpenAI | null;
}): EvaluatorFn {
  return createLlmJudge(
    "AnswerRelevancy",
    "You are a RAGAS-style answer relevancy judge. Score 0.0-1.0. Always include 'Score: X.X'.",
    (e) => {
      const input = toStr(collapseNamedData(e.evalInput));
      const output = toStr(collapseNamedData(e.evalOutput));
      return `Question: ${input}\nAnswer: ${output}\n\nHow relevant is the answer to the question?`;
    },
    opts,
  );
}

/** Answer correctness evaluator (RAGAS). */
export function AnswerCorrectness(opts?: {
  client?: OpenAI | null;
}): EvaluatorFn {
  return createLlmJudge(
    "AnswerCorrectness",
    "You are a RAGAS-style answer correctness judge. Score 0.0-1.0. Always include 'Score: X.X'.",
    (e) => {
      const input = toStr(collapseNamedData(e.evalInput));
      const output = toStr(collapseNamedData(e.evalOutput));
      const expected = toStr(resolveExpected(e));
      return `Question: ${input}\nAnswer: ${output}\nExpected: ${expected}\n\nHow correct is the answer?`;
    },
    opts,
  );
}
