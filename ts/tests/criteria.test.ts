import { describe, it, expect } from "vitest";
import { ScoreThreshold } from "../src/evals/criteria";
import type { Evaluation } from "../src/evals/evaluation";

// ── Test helpers ─────────────────────────────────────────────────────────────

function makeEval(score: number): Evaluation {
  return { score, reasoning: "test", details: {} };
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("ScoreThreshold", () => {
  it("uses default threshold=0.5 and pct=1.0", () => {
    const st = new ScoreThreshold();
    expect(st.threshold).toBe(0.5);
    expect(st.pct).toBe(1.0);
  });

  it("accepts custom threshold and pct", () => {
    const st = new ScoreThreshold(0.8, 0.9);
    expect(st.threshold).toBe(0.8);
    expect(st.pct).toBe(0.9);
  });

  describe("__call__", () => {
    it("passes when all inputs score above threshold", () => {
      const st = new ScoreThreshold(0.5);
      const results: Evaluation[][] = [
        [makeEval(0.8), makeEval(0.9)],
        [makeEval(0.7), makeEval(0.6)],
      ];
      const [passed, message] = st.__call__(results);
      expect(passed).toBe(true);
      expect(message).toContain("Pass");
      expect(message).toContain("2/2");
    });

    it("fails when not enough inputs pass", () => {
      const st = new ScoreThreshold(0.5, 1.0);
      const results: Evaluation[][] = [
        [makeEval(0.8)],
        [makeEval(0.3)], // below threshold
      ];
      const [passed, message] = st.__call__(results);
      expect(passed).toBe(false);
      expect(message).toContain("Fail");
      expect(message).toContain("1/2");
    });

    it("passes when pct requirement is met", () => {
      const st = new ScoreThreshold(0.5, 0.5);
      const results: Evaluation[][] = [
        [makeEval(0.8)],
        [makeEval(0.3)], // below threshold
      ];
      const [passed, message] = st.__call__(results);
      expect(passed).toBe(true);
    });

    it("fails when any evaluator for an input is below threshold", () => {
      const st = new ScoreThreshold(0.5);
      const results: Evaluation[][] = [
        [makeEval(0.8), makeEval(0.3)], // second eval fails
      ];
      const [passed, message] = st.__call__(results);
      expect(passed).toBe(false);
      expect(message).toContain("0/1");
    });

    it("handles empty results", () => {
      const st = new ScoreThreshold(0.5);
      const [passed, message] = st.__call__([]);
      expect(passed).toBe(false);
      expect(message).toContain("0/0");
    });

    it("includes threshold and pct in message", () => {
      const st = new ScoreThreshold(0.7, 0.8);
      const results: Evaluation[][] = [[makeEval(0.9)]];
      const [, message] = st.__call__(results);
      expect(message).toContain("0.7");
      expect(message).toContain("80.0%");
    });

    it("passes with exact threshold score", () => {
      const st = new ScoreThreshold(0.5);
      const results: Evaluation[][] = [[makeEval(0.5)]];
      const [passed] = st.__call__(results);
      expect(passed).toBe(true);
    });
  });
});
