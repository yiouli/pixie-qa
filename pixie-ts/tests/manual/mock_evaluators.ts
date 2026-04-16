/**
 * Mock evaluators and runnable for manual e2e testing — deterministic, no LLM calls.
 *
 * Usage:
 *   PIXIE_ROOT=/tmp/pixie_ts_e2e npx pixie-qa test tests/manual/datasets/sample-qa.json
 */

/**
 * Deterministic runnable for tests/manual/datasets/sample-qa.json.
 * Maps known questions to canned answers.
 */
export async function sampleQaRunnable(evalInput: unknown): Promise<string> {
  const input = evalInput as Record<string, unknown>;
  const question = String(input?.["question"] ?? "")
    .trim()
    .toLowerCase();

  const answers: Record<string, string> = {
    "what is the capital of france?": "The capital of France is Paris.",
    "what is 2 + 2?": "The answer is 4.",
    "who wrote hamlet?": "William Shakespeare wrote Hamlet.",
    "what is the boiling point of water?":
      "Water boils at 100 degrees Celsius at sea level.",
    "what is the largest planet?":
      "Jupiter is the largest planet in the solar system.",
  };

  return answers[question] ?? "";
}

/**
 * String-similarity evaluator. Scores high when output matches expected.
 */
export function SimpleFactualityEval() {
  return async (evaluable: {
    evalOutput: Array<{ value: unknown }>;
    expectation: unknown;
  }): Promise<{
    score: number;
    reasoning: string;
    details: Record<string, unknown>;
  }> => {
    const output = String(evaluable.evalOutput[0]?.value ?? "");
    const expected =
      evaluable.expectation === null || evaluable.expectation === undefined
        ? ""
        : String(evaluable.expectation);

    if (!expected) {
      return {
        score: 0.0,
        reasoning: "No expected output provided.",
        details: {},
      };
    }

    // Simple character-level similarity using longest common subsequence ratio
    const ratio = stringSimilarity(
      output.toLowerCase(),
      expected.toLowerCase(),
    );
    return {
      score: Math.round(ratio * 100) / 100,
      reasoning: `String similarity: ${(ratio * 100).toFixed(0)}% match between output and expected.`,
      details: { ratio },
    };
  };
}

/**
 * Keyword overlap evaluator. Requires high overlap to score well.
 */
export function StrictKeywordEval() {
  return async (evaluable: {
    evalOutput: Array<{ value: unknown }>;
    expectation: unknown;
  }): Promise<{
    score: number;
    reasoning: string;
    details: Record<string, unknown>;
  }> => {
    const output = String(evaluable.evalOutput[0]?.value ?? "").toLowerCase();
    const expected =
      evaluable.expectation === null || evaluable.expectation === undefined
        ? ""
        : String(evaluable.expectation);

    if (!expected) {
      return {
        score: 0.0,
        reasoning: "No expected output provided.",
        details: {},
      };
    }

    const expectedWords = new Set(
      expected.toLowerCase().split(/\s+/).filter(Boolean),
    );
    const outputWords = new Set(output.split(/\s+/).filter(Boolean));

    if (expectedWords.size === 0) {
      return { score: 1.0, reasoning: "No keywords to match.", details: {} };
    }

    let overlap = 0;
    for (const word of expectedWords) {
      if (outputWords.has(word)) overlap++;
    }
    const ratio = overlap / expectedWords.size;
    const label = ratio === 1.0 ? "All" : `${(ratio * 100).toFixed(0)}% of`;

    return {
      score: Math.round(ratio * 100) / 100,
      reasoning: `${label} expected keywords found in output.`,
      details: { overlap, total: expectedWords.size },
    };
  };
}

// Simple string similarity using SequenceMatcher-like ratio
function stringSimilarity(a: string, b: string): number {
  if (a === b) return 1.0;
  if (a.length === 0 || b.length === 0) return 0.0;

  // LCS-based similarity (approximation of Python's SequenceMatcher)
  const lcsLen = longestCommonSubsequenceLength(a, b);
  return (2 * lcsLen) / (a.length + b.length);
}

function longestCommonSubsequenceLength(a: string, b: string): number {
  const m = a.length;
  const n = b.length;
  // Use two rows to save memory
  let prev = new Array<number>(n + 1).fill(0);
  let curr = new Array<number>(n + 1).fill(0);

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (a[i - 1] === b[j - 1]) {
        curr[j] = prev[j - 1] + 1;
      } else {
        curr[j] = Math.max(prev[j], curr[j - 1]);
      }
    }
    [prev, curr] = [curr, prev];
    curr.fill(0);
  }
  return prev[n];
}
