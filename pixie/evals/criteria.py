"""Pre-made pass criteria for :func:`~pixie.evals.eval_utils.assert_pass`.

Provides :class:`ScoreThreshold`, a configurable criterion that checks
whether a sufficient fraction of test cases score above a threshold.
"""

from __future__ import annotations

from dataclasses import dataclass

from pixie.evals.evaluation import Evaluation


@dataclass
class ScoreThreshold:
    """Pass criteria: *pct* fraction of inputs must score >= *threshold* on all evaluators.

    Uses "at least one pass" semantics: when running multiple passes, the
    test passes if **any** single pass meets the criteria.  This is useful
    for non-deterministic LLM outputs — "can the system ever produce good
    output" vs. "does it always."

    Attributes:
        threshold: Minimum score an individual evaluation must reach.
        pct: Fraction of test-case inputs (0.0–1.0) that must pass.
    """

    threshold: float = 0.5
    pct: float = 1.0

    def __call__(
        self,
        results: list[list[list[Evaluation]]],
    ) -> tuple[bool, str]:
        """Evaluate the results tensor and return ``(passed, message)``.

        Args:
            results: Shape ``[passes][inputs][evaluators]``.

        Returns:
            A ``(bool, str)`` tuple: whether the criteria are met and a
            human-readable explanation.
        """
        best_passing = 0
        best_pass_idx = 0
        total_passes = len(results)

        for p_idx, pass_results in enumerate(results):
            total_inputs = len(pass_results)
            passing_inputs = 0
            for input_evals in pass_results:
                all_pass = all(e.score >= self.threshold for e in input_evals)
                if all_pass:
                    passing_inputs += 1
            if total_inputs > 0 and passing_inputs / total_inputs >= self.pct:
                pct_actual = passing_inputs / total_inputs * 100
                return (
                    True,
                    f"Pass (pass {p_idx + 1}/{total_passes}): "
                    f"{passing_inputs}/{total_inputs} inputs ({pct_actual:.1f}%) "
                    f"scored >= {self.threshold} on all evaluators "
                    f"(required: {self.pct * 100:.1f}%)",
                )
            if passing_inputs > best_passing:
                best_passing = passing_inputs
                best_pass_idx = p_idx

        # No pass met the criteria
        total_inputs = len(results[best_pass_idx]) if results else 0
        pct_best = best_passing / total_inputs * 100 if total_inputs > 0 else 0.0
        return (
            False,
            f"Fail: best pass was {best_pass_idx + 1}/{total_passes} "
            f"with {best_passing}/{total_inputs} inputs ({pct_best:.1f}%) "
            f"scoring >= {self.threshold} on all evaluators "
            f"(required: {self.pct * 100:.1f}%)",
        )
