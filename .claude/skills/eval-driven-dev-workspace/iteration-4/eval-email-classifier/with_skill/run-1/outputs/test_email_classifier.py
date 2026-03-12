"""Eval-based tests for the email classifier.

Tests verify that extract_from_email always returns a dict with:
  - "category" in {"billing", "technical", "account", "general"}
  - "priority"  in {"low", "medium", "high"}
  - "summary"   a non-empty string

Uses heuristic evaluators only — no API key required.
"""

import json

from pixie import enable_storage
from pixie.evals import (
    assert_dataset_pass,
    Evaluation,
    ScoreThreshold,
    root,
)
from pixie.storage.evaluable import Evaluable

from extractor import extract_from_email

VALID_CATEGORIES = {"billing", "technical", "account", "general"}
VALID_PRIORITIES = {"low", "medium", "high"}


def runnable(eval_input):
    """Adapter: re-run the app with eval_input captured by @observe."""
    enable_storage()
    extract_from_email(**eval_input)


# ---------------------------------------------------------------------------
# Custom evaluator: checks JSON structure and enum values
# ---------------------------------------------------------------------------

async def json_structure_eval(evaluable: Evaluable, *, trace=None) -> Evaluation:
    """Verify output has required keys with valid enum values."""
    output = evaluable.eval_output

    # eval_output is the dict returned by extract_from_email
    if not isinstance(output, dict):
        # Try to parse if it's a JSON string
        try:
            output = json.loads(output)
        except Exception:
            return Evaluation(
                score=0.0,
                reasoning=f"Output is not a dict and cannot be parsed as JSON: {type(output)!r}",
            )

    missing_keys = [k for k in ("category", "priority", "summary") if k not in output]
    if missing_keys:
        return Evaluation(
            score=0.0,
            reasoning=f"Missing required keys: {missing_keys}",
        )

    errors = []
    if output["category"] not in VALID_CATEGORIES:
        errors.append(f"category {output['category']!r} not in {VALID_CATEGORIES}")
    if output["priority"] not in VALID_PRIORITIES:
        errors.append(f"priority {output['priority']!r} not in {VALID_PRIORITIES}")
    if not isinstance(output["summary"], str) or not output["summary"].strip():
        errors.append("summary must be a non-empty string")

    if errors:
        return Evaluation(score=0.0, reasoning="; ".join(errors))

    return Evaluation(score=1.0, reasoning="All required keys present with valid values.")


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

async def test_json_structure():
    """Every item in the dataset must have valid JSON structure."""
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name="email-classifier-golden",
        evaluators=[json_structure_eval],
        pass_criteria=ScoreThreshold(threshold=1.0, pct=1.0),
        from_trace=root,
    )
