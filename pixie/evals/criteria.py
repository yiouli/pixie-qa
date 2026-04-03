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

    Attributes:
        threshold: Minimum score an individual evaluation must reach.
        pct: Fraction of test-case inputs (0.0–1.0) that must pass.
    """

    threshold: float = 0.5
    pct: float = 1.0

    def __call__(
        self,
        results: list[list[Evaluation]],
    ) -> tuple[bool, str]:
        """Evaluate the results matrix and return ``(passed, message)``.

        Args:
            results: Shape ``[inputs][evaluators]``.

        Returns:
            A ``(bool, str)`` tuple: whether the criteria are met and a
            human-readable explanation.
        """
        total_inputs = len(results)
        passing_inputs = 0
        for input_evals in results:
            all_pass = all(e.score >= self.threshold for e in input_evals)
            if all_pass:
                passing_inputs += 1

        if total_inputs > 0 and passing_inputs / total_inputs >= self.pct:
            pct_actual = passing_inputs / total_inputs * 100
            return (
                True,
                f"Pass: {passing_inputs}/{total_inputs} inputs ({pct_actual:.1f}%) "
                f"scored >= {self.threshold} on all evaluators "
                f"(required: {self.pct * 100:.1f}%)",
            )

        pct_best = passing_inputs / total_inputs * 100 if total_inputs > 0 else 0.0
        return (
            False,
            f"Fail: {passing_inputs}/{total_inputs} inputs ({pct_best:.1f}%) "
            f"scored >= {self.threshold} on all evaluators "
            f"(required: {self.pct * 100:.1f}%)",
        )
