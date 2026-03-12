"""Eval-based tests for the email classifier.

Run with:
  cd /home/yiouli/repo/pixie-qa/.claude/skills/eval-driven-dev-workspace/iteration-3/eval-email-classifier/with_skill/project
  PYTHONPATH=/home/yiouli/repo/pixie-qa pixie-test tests/ -v

These tests check that every output from extract_from_email has:
  - Valid JSON structure (is a dict / serializable)
  - Required keys: category, priority, summary
  - category value is one of: billing, technical, account, general
  - priority value is one of: low, medium, high
  - summary is a non-empty string
"""

import json
from pixie import enable_storage
from pixie.evals import (
    assert_dataset_pass,
    ScoreThreshold,
    Evaluation,
    root,
)
from pixie.storage.evaluable import Evaluable


# ---------------------------------------------------------------------------
# Custom evaluator: checks JSON structure of the extractor output
# ---------------------------------------------------------------------------

VALID_CATEGORIES = {"billing", "technical", "account", "general"}
VALID_PRIORITIES = {"low", "medium", "high"}


async def json_structure_eval(evaluable: Evaluable, *, trace=None) -> Evaluation:
    """Evaluate that the output dict has the expected structure and valid enum values."""
    output = evaluable.eval_output

    # Must be a dict
    if not isinstance(output, dict):
        return Evaluation(
            score=0.0,
            reasoning=f"Expected dict output, got {type(output).__name__}",
        )

    # Must be JSON-serializable
    try:
        json.dumps(output)
    except (TypeError, ValueError) as exc:
        return Evaluation(
            score=0.0,
            reasoning=f"Output is not JSON-serializable: {exc}",
        )

    errors = []

    # Required keys
    for key in ("category", "priority", "summary"):
        if key not in output:
            errors.append(f"Missing required key: '{key}'")

    # Category enum
    category = output.get("category")
    if category is not None and category not in VALID_CATEGORIES:
        errors.append(f"Invalid category '{category}', must be one of {sorted(VALID_CATEGORIES)}")

    # Priority enum
    priority = output.get("priority")
    if priority is not None and priority not in VALID_PRIORITIES:
        errors.append(f"Invalid priority '{priority}', must be one of {sorted(VALID_PRIORITIES)}")

    # Summary must be a non-empty string
    summary = output.get("summary", "")
    if not isinstance(summary, str) or not summary.strip():
        errors.append("'summary' must be a non-empty string")

    if errors:
        return Evaluation(
            score=0.0,
            reasoning="Structure validation failed: " + "; ".join(errors),
            details={"errors": errors, "output": output},
        )

    return Evaluation(
        score=1.0,
        reasoning=(
            f"Output is valid: category='{category}', priority='{priority}', "
            f"summary length={len(summary)}"
        ),
    )


# ---------------------------------------------------------------------------
# Runnable adapter
# ---------------------------------------------------------------------------

def runnable(eval_input):
    """Call extract_from_email with the eval_input dict from the dataset."""
    enable_storage()
    # eval_input was captured as {"email_text": str} by @observe
    from extractor import extract_from_email
    email_text = eval_input.get("email_text", "") if isinstance(eval_input, dict) else eval_input
    extract_from_email(email_text=email_text)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_json_structure():
    """All classifier outputs must have valid JSON structure with correct keys and enum values."""
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name="email-classifier-golden",
        evaluators=[json_structure_eval],
        pass_criteria=ScoreThreshold(threshold=1.0, pct=1.0),
        from_trace=root,
    )
