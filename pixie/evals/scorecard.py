"""Scorecard data models, collector, and HTML report generation.

This module provides:

- :class:`AssertRecord` — results from a single ``assert_pass``/``assert_dataset_pass`` call.
- :class:`TestRecord` — aggregated results for one test function.
- :class:`ScorecardReport` — full report for a ``pixie test`` run.
- :class:`ScorecardCollector` — thread-safe context-local collector.
- :func:`generate_scorecard_html` — render a ``ScorecardReport`` as self-contained HTML.
- :func:`save_scorecard` — write HTML to ``{config.root}/scorecards/<timestamp>.html``.
"""

from __future__ import annotations

import importlib.resources
import json
import os
import threading
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from pixie.evals.evaluation import Evaluation

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AssertRecord:
    """Results from one ``assert_pass`` / ``assert_dataset_pass`` call.

    Attributes:
        evaluator_names: Display names for each evaluator, in order.
        input_labels: Display labels for each eval input, in order.
        results: Shape ``[inputs][evaluators]`` — the evaluation
            matrix returned by ``assert_pass``.
        passed: Whether the assertion passed.
        criteria_message: Human-readable summary from the pass criteria.
        scoring_strategy: Human-readable description of the scoring approach.
    """

    evaluator_names: tuple[str, ...]
    input_labels: tuple[str, ...]
    results: list[list[Evaluation]]
    passed: bool
    criteria_message: str
    scoring_strategy: str
    evaluable_dicts: tuple[dict[str, Any], ...] = field(default_factory=tuple)


@dataclass
class TestRecord:
    """Aggregated results for one test function.

    Attributes:
        name: Test display name (``file.py::function``).
        status: Overall test outcome.
        message: Error/failure message, if any.
        asserts: Ordered list of ``AssertRecord``s collected during the test.
    """

    __test__ = False  # prevent pytest from collecting this dataclass

    name: str
    status: Literal["passed", "failed", "error"]
    message: str | None = None
    asserts: list[AssertRecord] = field(default_factory=list)


@dataclass
class ScorecardReport:
    """Full report for a ``pixie test`` run.

    Attributes:
        command_args: The command-line arguments string.
        test_records: One ``TestRecord`` per discovered test function.
        timestamp: When the test run occurred (UTC).
    """

    command_args: str
    test_records: list[TestRecord]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Collector — accumulates AssertRecords for the current test function
# ---------------------------------------------------------------------------

#: Context var holding the active collector (if any).
_collector_var: ContextVar[ScorecardCollector | None] = ContextVar(
    "_scorecard_collector", default=None
)


class ScorecardCollector:
    """Thread-safe collector that accumulates :class:`AssertRecord` instances.

    Intended to be activated via :meth:`activate` before running a test
    function, and deactivated via :meth:`deactivate` afterwards. While
    active, ``assert_pass`` pushes records here.
    """

    def __init__(self) -> None:
        self._records: list[AssertRecord] = []
        self._lock = threading.Lock()
        self._token: object | None = None

    def activate(self) -> None:
        """Set this collector as the current context-local collector."""
        self._token = _collector_var.set(self)

    def deactivate(self) -> None:
        """Remove this collector from the context."""
        if self._token is not None:
            _collector_var.reset(self._token)  # type: ignore[arg-type]
            self._token = None

    def record(self, assert_record: AssertRecord) -> None:
        """Thread-safely append an ``AssertRecord``."""
        with self._lock:
            self._records.append(assert_record)

    def drain(self) -> list[AssertRecord]:
        """Return all collected records and clear the internal list."""
        with self._lock:
            records = list(self._records)
            self._records.clear()
            return records


def get_active_collector() -> ScorecardCollector | None:
    """Return the currently active :class:`ScorecardCollector`, if any."""
    return _collector_var.get()


# ---------------------------------------------------------------------------
# Evaluator naming
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


def _input_label(inp: object) -> str:
    """Derive a short display label from an eval input.

    Truncates long strings to keep the scorecard readable.
    """
    s = str(inp)
    return s[:80] + "…" if len(s) > 80 else s


# ---------------------------------------------------------------------------
# Scoring strategy description
# ---------------------------------------------------------------------------


def _describe_criteria(criteria: object) -> str:
    """Return a human-readable description of the pass criteria.

    Recognises :class:`~pixie.evals.criteria.ScoreThreshold` explicitly;
    falls back to the object's repr for custom callables.
    """
    # Import here to avoid circular imports
    from pixie.evals.criteria import ScoreThreshold

    if isinstance(criteria, ScoreThreshold):
        pct_str = f"{criteria.pct * 100:.0f}%"
        return (
            f"Each evaluator score must be ≥ {criteria.threshold}. "
            f"At least {pct_str} of test-case inputs must pass on all evaluators."
        )
    # Custom callable — use repr
    return f"Custom criteria: {repr(criteria)}"


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


def _report_to_dict(report: ScorecardReport) -> dict[str, Any]:
    """Serialize a :class:`ScorecardReport` into a JSON-friendly dict.

    The returned dict matches the ``ScorecardReportData`` TypeScript
    interface consumed by the React frontend.
    """
    ts = report.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
    total = len(report.test_records)
    passed = sum(1 for tr in report.test_records if tr.status == "passed")

    return {
        "command_args": report.command_args,
        "timestamp": ts,
        "summary": f"{passed}/{total} tests passed",
        "pixie_repo_url": _PIXIE_REPO_URL,
        "feedback_url": _PIXIE_FEEDBACK_URL,
        "brand_icon_url": _PIXIE_BRAND_ICON_URL,
        "test_records": [
            {
                "name": tr.name,
                "status": tr.status,
                "message": tr.message,
                "asserts": [
                    {
                        "evaluator_names": list(ar.evaluator_names),
                        "input_labels": list(ar.input_labels),
                        "results": [
                            [
                                {
                                    "score": ev.score,
                                    "reasoning": ev.reasoning,
                                    "details": ev.details,
                                }
                                for ev in inp_evals
                            ]
                            for inp_evals in ar.results
                        ],
                        "passed": ar.passed,
                        "criteria_message": ar.criteria_message,
                        "scoring_strategy": ar.scoring_strategy,
                        "evaluable_dicts": [
                            {
                                "input": d.get("input"),
                                "expected_output": d.get("expected_output"),
                                "actual_output": d.get("actual_output"),
                                "metadata": d.get("metadata"),
                            }
                            for d in ar.evaluable_dicts
                        ],
                    }
                    for ar in tr.asserts
                ],
            }
            for tr in report.test_records
        ],
    }


def generate_scorecard_html(report: ScorecardReport) -> str:
    """Render a :class:`ScorecardReport` as a self-contained HTML page.

    Loads the pre-compiled React template from ``pixie/assets/index.html``
    and injects the serialized report data via string replacement.

    Args:
        report: The scorecard report to render.

    Returns:
        Complete HTML document as a string.
    """
    template = _load_template()
    data = _report_to_dict(report)
    data_json = json.dumps(data)
    return template.replace(_DATA_PLACEHOLDER, data_json)


# ---------------------------------------------------------------------------
# Save to disk
# ---------------------------------------------------------------------------


def save_scorecard(report: ScorecardReport) -> str:
    """Generate and save the scorecard HTML to disk.

    Saves to ``{config.root}/scorecards/<timestamp>-<normalized>.html``.

    Args:
        report: The scorecard report to save.

    Returns:
        The absolute path of the saved HTML file.
    """
    from pixie.config import get_config

    config = get_config()
    scorecard_dir = os.path.join(config.root, "scorecards")
    os.makedirs(scorecard_dir, exist_ok=True)

    # Build filename from timestamp and command args
    ts_str = report.timestamp.strftime("%Y%m%d-%H%M%S")
    # Normalise command args into a safe filename fragment
    safe_args = _normalise_filename(report.command_args)
    filename = f"{ts_str}-{safe_args}.html" if safe_args else f"{ts_str}.html"
    filepath = os.path.join(scorecard_dir, filename)

    html_content = generate_scorecard_html(report)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    return os.path.abspath(filepath)


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
