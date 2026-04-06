"""Mock evaluators for manual e2e testing — deterministic, no LLM calls.

These produce realistic Evaluation results using simple heuristics.
No API keys or network calls required.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from pixie.evals.evaluation import Evaluation
from pixie.storage.evaluable import Evaluable, _Unset


def sample_qa_runnable(eval_input: object) -> str:
    """Deterministic runnable for tests/manual/datasets/sample-qa.json."""
    if isinstance(eval_input, dict):
        question = str(eval_input.get("question", "")).strip().lower()
    else:
        question = str(eval_input).strip().lower()

    answers = {
        "what is the capital of france?": "The capital of France is Paris.",
        "what is 2 + 2?": "The answer is 4.",
        "who wrote hamlet?": "William Shakespeare wrote Hamlet.",
        "what is the boiling point of water?": (
            "Water boils at 100 degrees Celsius at sea level."
        ),
        "what is the largest planet?": ("Jupiter is the largest planet in the solar system."),
    }
    return answers.get(question, "")


class SimpleFactualityEval:
    """String-similarity evaluator. Scores high when output matches expected."""

    name = "Factuality"

    def __call__(
        self,
        evaluable: Evaluable,
    ) -> Evaluation:
        output = str(evaluable.eval_output or "")
        expected = (
            ""
            if isinstance(evaluable.expected_output, _Unset)
            else str(evaluable.expected_output or "")
        )
        if not expected:
            return Evaluation(score=0.0, reasoning="No expected output provided.")

        ratio = SequenceMatcher(None, output.lower(), expected.lower()).ratio()
        return Evaluation(
            score=round(ratio, 2),
            reasoning=f"String similarity: {ratio:.0%} match between output and expected.",
        )


class StrictKeywordEval:
    """Keyword overlap evaluator. Strict — requires high overlap to pass."""

    name = "KeywordMatch"

    def __call__(
        self,
        evaluable: Evaluable,
    ) -> Evaluation:
        output = str(evaluable.eval_output or "").lower()
        expected = (
            ""
            if isinstance(evaluable.expected_output, _Unset)
            else str(evaluable.expected_output or "")
        )
        if not expected:
            return Evaluation(score=0.0, reasoning="No expected output provided.")

        expected_words = set(expected.lower().split())
        output_words = set(output.split())
        if not expected_words:
            return Evaluation(score=1.0, reasoning="No keywords to match.")

        overlap = len(expected_words & output_words) / len(expected_words)
        passed = "All" if overlap == 1.0 else f"{overlap:.0%} of"
        return Evaluation(
            score=round(overlap, 2),
            reasoning=f"{passed} expected keywords found in output.",
        )
