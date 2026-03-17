"""Mock evaluators for e2e testing — deterministic, no LLM calls.

These evaluators simulate the behavior of real LLM-as-judge evaluators
(FactualityEval, ClosedQAEval, etc.) using simple string-matching
heuristics. They produce realistic Evaluation results with scores and
reasoning, enabling full ``pixie test`` e2e verification without API
keys, network calls, or non-deterministic outputs.

Each mock evaluator is a callable matching the pixie Evaluator protocol.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from pixie.evals.evaluation import Evaluation
from pixie.storage.evaluable import Evaluable, _Unset
from pixie.storage.tree import ObservationNode


class MockFactualityEval:
    """Deterministic factuality evaluator using string similarity.

    Compares ``eval_output`` against ``expected_output`` using
    SequenceMatcher. Threshold for pass is 0.4 (lenient, simulating
    an LLM judge that accepts paraphrases).
    """

    name = "MockFactuality"

    def __call__(
        self,
        evaluable: Evaluable,
        *,
        trace: list[ObservationNode] | None = None,
    ) -> Evaluation:
        output = str(evaluable.eval_output or "")
        expected = (
            ""
            if isinstance(evaluable.expected_output, _Unset)
            else str(evaluable.expected_output or "")
        )

        if not expected:
            return Evaluation(
                score=0.0,
                reasoning="No expected output provided for factuality check.",
            )

        ratio = SequenceMatcher(None, output.lower(), expected.lower()).ratio()
        score = min(ratio * 1.5, 1.0)  # boost similarity for paraphrases
        passed = score >= 0.5

        return Evaluation(
            score=round(score, 2),
            reasoning=(
                f"Output is {'factually consistent' if passed else 'not consistent'} "
                f"with expected answer (similarity: {ratio:.2f})."
            ),
        )


class MockClosedQAEval:
    """Deterministic closed-QA evaluator using keyword overlap.

    Checks how many significant words from ``expected_output`` appear
    in ``eval_output``.
    """

    name = "MockClosedQA"

    def __call__(
        self,
        evaluable: Evaluable,
        *,
        trace: list[ObservationNode] | None = None,
    ) -> Evaluation:
        output = str(evaluable.eval_output or "").lower()
        expected = (
            ""
            if isinstance(evaluable.expected_output, _Unset)
            else str(evaluable.expected_output or "")
        )

        if not expected:
            return Evaluation(score=0.0, reasoning="No expected output to compare.")

        # Extract significant words (>3 chars) from expected
        expected_words = {
            w for w in expected.lower().split() if len(w) > 3 and w.isalpha()
        }
        if not expected_words:
            return Evaluation(score=1.0, reasoning="No significant keywords to check.")

        found = sum(1 for w in expected_words if w in output)
        score = found / len(expected_words)

        return Evaluation(
            score=round(score, 2),
            reasoning=(
                f"Found {found}/{len(expected_words)} key terms "
                f"from expected answer. "
                + (
                    "Answer covers the expected content."
                    if score >= 0.5
                    else "Answer missing key information."
                )
            ),
        )


class MockHallucinationEval:
    """Deterministic hallucination detector — always passes.

    In a real system this would use an LLM to check for fabricated
    facts. The mock version always returns a high score, simulating
    an output that doesn't hallucinate.
    """

    name = "MockHallucination"

    def __call__(
        self,
        evaluable: Evaluable,
        *,
        trace: list[ObservationNode] | None = None,
    ) -> Evaluation:
        output = str(evaluable.eval_output or "")
        if not output.strip():
            return Evaluation(score=0.0, reasoning="Empty output — cannot evaluate.")

        # Simple heuristic: presence of hedging language is good
        return Evaluation(
            score=0.95,
            reasoning="No hallucinations detected in the output.",
        )


class MockFailingEval:
    """Evaluator that always returns a low score — useful for testing failure paths.

    Simulates an evaluator that detects problems in every output.
    """

    name = "MockStrictTone"

    def __call__(
        self,
        evaluable: Evaluable,
        *,
        trace: list[ObservationNode] | None = None,
    ) -> Evaluation:
        return Evaluation(
            score=0.2,
            reasoning="Output does not match the required formal tone guidelines.",
        )
