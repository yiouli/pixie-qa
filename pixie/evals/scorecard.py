"""Scorecard data models and HTML report generation.

This module provides:

- :class:`DatasetEntryResult` — evaluation results for a single dataset entry.
- :class:`DatasetScorecard` — per-dataset scorecard with non-uniform evaluators per row.
- :func:`generate_dataset_scorecard_html` — render a ``DatasetScorecard`` as self-contained HTML.
- :func:`save_dataset_scorecard` — write HTML to
  ``{config.root}/scorecards/<timestamp>-<name>.html``.
"""

from __future__ import annotations

import importlib.resources
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from pixie.evals.evaluation import Evaluation

# ---------------------------------------------------------------------------
# Helper: evaluator display name
# ---------------------------------------------------------------------------


def _evaluator_display_name(evaluator: object) -> str:
    """Derive a human-readable name from an evaluator callable.

    Tries, in order:
        1. ``evaluator.name`` attribute (e.g. ``AutoevalsAdapter.name``).
        2. ``type(evaluator).__name__`` for class instances.
        3. ``evaluator.__name__`` for plain functions.
        4. ``repr(evaluator)`` as a last resort.
    """
    name_attr = getattr(evaluator, "name", None)  # noqa: B009
    if isinstance(name_attr, str):
        return name_attr
    func_name = getattr(evaluator, "__name__", None)  # noqa: B009
    if isinstance(func_name, str):
        return func_name
    cls_name = type(evaluator).__name__
    if cls_name != "function":
        return cls_name
    return repr(evaluator)  # pragma: no cover


# ---------------------------------------------------------------------------
# HTML generation (template-based)
# ---------------------------------------------------------------------------

_PIXIE_REPO_URL = "https://github.com/yiouli/pixie-qa"
_PIXIE_FEEDBACK_URL = "https://feedback.gopixie.ai/feedback"
_PIXIE_BRAND_ICON_URL = (
    "https://github.com/user-attachments/assets/76c18199-f00a-4fb3-a12f-ce6c173727af"
)

_DATA_PLACEHOLDER = '"__PIXIE_DATA_PLACEHOLDER__"'


def _load_template() -> str:
    """Load the compiled React scorecard HTML template.

    Uses ``importlib.resources`` to locate the built ``index.html``
    inside the ``pixie.assets`` package. The template contains a
    ``__PIXIE_DATA_PLACEHOLDER__`` string that gets replaced with actual
    report data at generation time.

    Returns:
        The raw HTML template string.

    Raises:
        FileNotFoundError: If the compiled template has not been built.
    """
    assets = importlib.resources.files("pixie.assets")
    template_path = assets / "index.html"
    return template_path.read_text(encoding="utf-8")


def _normalise_filename(s: str) -> str:
    """Convert an arbitrary string into a safe filename fragment.

    Replaces non-alphanumeric characters with hyphens and collapses
    consecutive hyphens.  Truncates to 60 characters.
    """
    chars: list[str] = []
    for c in s:
        if c.isalnum() or c in ("_", "-"):
            chars.append(c)
        else:
            chars.append("-")
    result = "".join(chars).strip("-")
    # Collapse consecutive hyphens
    while "--" in result:
        result = result.replace("--", "-")
    return result[:60]


# ---------------------------------------------------------------------------
# Dataset scorecard models — per-dataset, non-uniform evaluators per row
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DatasetEntryResult:
    """Evaluation results for a single dataset entry.

    Each entry may have a different set of evaluators, so
    ``evaluator_names`` and ``evaluations`` are parallel tuples
    whose length can vary across entries.

    Attributes:
        evaluator_names: Display names of evaluators applied to this entry.
        evaluations: Results, parallel to *evaluator_names*.
        input_label: Short display label for the entry's input.
        evaluable_dict: Context dict with input/expected/actual/metadata.
    """

    evaluator_names: tuple[str, ...]
    evaluations: tuple[Evaluation, ...]
    input_label: str
    evaluable_dict: dict[str, Any]


@dataclass
class DatasetScorecard:
    """Scorecard for a single dataset evaluation run.

    Contains one :class:`DatasetEntryResult` per dataset row that had
    evaluators defined. Each row has its own (possibly different) set
    of evaluators.

    Attributes:
        dataset_name: Name of the dataset.
        entries: Per-row evaluation results.
        timestamp: When the evaluation was executed (UTC).
    """

    dataset_name: str
    entries: list[DatasetEntryResult]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def _dataset_scorecard_to_dict(
    scorecard: DatasetScorecard,
    command_args: str,
) -> dict[str, Any]:
    """Serialize a :class:`DatasetScorecard` as a report dict.

    Maps the dataset scorecard into the existing React frontend format
    by creating one test record for the dataset, with one assert record
    per entry (each having its own evaluator set).
    """
    ts = scorecard.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

    # Count passed entries (all evaluators score >= 0.5)
    passed_entries = sum(
        1
        for entry in scorecard.entries
        if all(e.score >= 0.5 for e in entry.evaluations)
    )
    total_entries = len(scorecard.entries)

    # Map each entry to an AssertRecord-shaped dict
    assert_dicts: list[dict[str, Any]] = []
    for entry in scorecard.entries:
        assert_dicts.append(
            {
                "evaluator_names": list(entry.evaluator_names),
                "input_labels": [entry.input_label],
                "results": [
                    [
                        {
                            "score": ev.score,
                            "reasoning": ev.reasoning,
                            "details": ev.details,
                        }
                        for ev in entry.evaluations
                    ]
                ],
                "passed": all(e.score >= 0.5 for e in entry.evaluations),
                "criteria_message": "",
                "scoring_strategy": "",
                "evaluable_dicts": [entry.evaluable_dict],
            }
        )

    # Determine overall status
    all_pass = passed_entries == total_entries
    status: Literal["passed", "failed"] = "passed" if all_pass else "failed"

    return {
        "command_args": command_args,
        "timestamp": ts,
        "summary": f"{passed_entries}/{total_entries} entries passed",
        "pixie_repo_url": _PIXIE_REPO_URL,
        "feedback_url": _PIXIE_FEEDBACK_URL,
        "brand_icon_url": _PIXIE_BRAND_ICON_URL,
        "test_records": [
            {
                "name": scorecard.dataset_name,
                "status": status,
                "message": None,
                "asserts": assert_dicts,
            }
        ],
    }


def generate_dataset_scorecard_html(
    scorecard: DatasetScorecard,
    command_args: str,
) -> str:
    """Render a :class:`DatasetScorecard` as a self-contained HTML page."""
    template = _load_template()
    data = _dataset_scorecard_to_dict(scorecard, command_args)
    data_json = json.dumps(data)
    return template.replace(_DATA_PLACEHOLDER, data_json)


def save_dataset_scorecard(
    scorecard: DatasetScorecard,
    command_args: str,
) -> str:
    """Generate and save a dataset scorecard HTML to disk.

    Saves to ``{config.root}/scorecards/<timestamp>-<dataset_name>.html``.

    Args:
        scorecard: The dataset scorecard to save.
        command_args: The command-line arguments string.

    Returns:
        The absolute path of the saved HTML file.
    """
    from pixie.config import get_config

    config = get_config()
    scorecard_dir = os.path.join(config.root, "scorecards")
    os.makedirs(scorecard_dir, exist_ok=True)

    ts_str = scorecard.timestamp.strftime("%Y%m%d-%H%M%S")
    safe_name = _normalise_filename(scorecard.dataset_name)
    filename = f"{ts_str}-{safe_name}.html" if safe_name else f"{ts_str}.html"
    filepath = os.path.join(scorecard_dir, filename)

    html_content = generate_dataset_scorecard_html(scorecard, command_args)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    return os.path.abspath(filepath)
