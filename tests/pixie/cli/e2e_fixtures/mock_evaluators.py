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


def customer_faq_runnable(eval_input: object) -> str:
    """Deterministic runnable for customer-faq fixture dataset."""
    if isinstance(eval_input, dict):
        message = str(eval_input.get("user_message", "")).strip().lower()
    else:
        message = str(eval_input).strip().lower()

    answers = {
        "what is the baggage allowance?": (
            "You may bring one carry-on bag weighing up to 50 pounds, "
            "with maximum dimensions of 22 x 14 x 9 inches."
        ),
        "how many seats are on the plane?": (
            "There are 120 seats total — 22 business class and 98 economy. "
            "Exit rows are at rows 4 and 16."
        ),
        "is there wifi on the plane?": (
            "Yes, we offer complimentary wifi. Connect to the network named "
            "Airline-Wifi once on board."
        ),
        "what is the cancellation policy?": (
            "You can cancel your booking up to 24 hours before departure for "
            "a full refund. Cancellations within 24 hours incur a $50 fee."
        ),
        "do you serve meals on the flight?": (
            "We serve complimentary snacks and beverages on all flights. "
            "Business class passengers receive a full meal service."
        ),
    }
    return answers.get(message, "")


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
    ) -> Evaluation:
        return Evaluation(
            score=0.2,
            reasoning="Output does not match the required formal tone guidelines.",
        )
