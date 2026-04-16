/**
 * Mock evaluators and runnable for automated e2e testing — deterministic, no LLM calls.
 *
 * These are used by the automated e2e test suite (tests/e2e.test.ts)
 * to verify the full pixie-qa pipeline without API keys.
 */

/**
 * Deterministic runnable for e2e_fixtures/datasets/customer-faq.json.
 */
export async function customerFaqRunnable(evalInput: unknown): Promise<string> {
  const input = evalInput as Record<string, unknown>;
  const message = String(input?.["user_message"] ?? "")
    .trim()
    .toLowerCase();

  const answers: Record<string, string> = {
    "what is the baggage allowance?":
      "You may bring one carry-on bag weighing up to 50 pounds, " +
      "with maximum dimensions of 22 x 14 x 9 inches.",
    "how many seats are on the plane?":
      "There are 120 seats total — 22 business class and 98 economy. " +
      "Exit rows are at rows 4 and 16.",
    "is there wifi on the plane?":
      "Yes, we offer complimentary wifi. Connect to the network named " +
      "Airline-Wifi once on board.",
    "what is the cancellation policy?":
      "You can cancel your booking up to 24 hours before departure for " +
      "a full refund. Cancellations within 24 hours incur a $50 fee.",
    "do you serve meals on the flight?":
      "We serve complimentary snacks and beverages on all flights. " +
      "Business class passengers receive a full meal service.",
  };

  return answers[message] ?? "";
}

/**
 * SequenceMatcher-style string similarity evaluator.
 * Most items pass with high scores.
 */
export function MockFactualityEval() {
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
      evaluable.expectation == null
        ? ""
        : String(evaluable.expectation).toLowerCase();

    if (!expected) {
      return { score: 0.0, reasoning: "No expected output", details: {} };
    }

    const ratio = lcsRatio(output, expected);
    return {
      score: Math.round(ratio * 100) / 100,
      reasoning: `String similarity: ${(ratio * 100).toFixed(0)}%`,
      details: { ratio },
    };
  };
}

/**
 * Keyword overlap evaluator — strict, some items may fail.
 */
export function MockClosedQAEval() {
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
      evaluable.expectation == null
        ? ""
        : String(evaluable.expectation).toLowerCase();

    if (!expected) {
      return { score: 0.0, reasoning: "No expected output", details: {} };
    }

    const expectedWords = new Set(expected.split(/\s+/).filter(Boolean));
    const outputWords = new Set(output.split(/\s+/).filter(Boolean));
    let overlap = 0;
    for (const w of expectedWords) {
      if (outputWords.has(w)) overlap++;
    }
    const ratio = expectedWords.size > 0 ? overlap / expectedWords.size : 1.0;

    return {
      score: Math.round(ratio * 100) / 100,
      reasoning: `Keyword overlap: ${overlap}/${expectedWords.size}`,
      details: { overlap, total: expectedWords.size },
    };
  };
}

/**
 * Always-pass evaluator — returns score 0.95.
 */
export function MockHallucinationEval() {
  return async (): Promise<{
    score: number;
    reasoning: string;
    details: Record<string, unknown>;
  }> => ({
    score: 0.95,
    reasoning: "Fixed score: 0.95",
    details: {},
  });
}

/**
 * Always-fail evaluator — returns score 0.2.
 */
export function MockStrictTone() {
  return async (): Promise<{
    score: number;
    reasoning: string;
    details: Record<string, unknown>;
  }> => ({
    score: 0.2,
    reasoning: "Fixed score: 0.2",
    details: {},
  });
}

// ── Helpers ──────────────────────────────────────────────────────

function lcsRatio(a: string, b: string): number {
  if (a === b) return 1.0;
  if (!a.length || !b.length) return 0.0;
  const len = lcsLength(a, b);
  return (2 * len) / (a.length + b.length);
}

function lcsLength(a: string, b: string): number {
  const m = a.length;
  const n = b.length;
  let prev = new Array<number>(n + 1).fill(0);
  let curr = new Array<number>(n + 1).fill(0);
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      curr[j] =
        a[i - 1] === b[j - 1]
          ? prev[j - 1] + 1
          : Math.max(prev[j], curr[j - 1]);
    }
    [prev, curr] = [curr, prev];
    curr.fill(0);
  }
  return prev[n];
}
