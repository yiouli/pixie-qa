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

import html
import os
import threading
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

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
        results: Shape ``[passes][inputs][evaluators]`` — the evaluation
            tensor returned by ``assert_pass``.
        passed: Whether the assertion passed.
        criteria_message: Human-readable summary from the pass criteria.
        scoring_strategy: Human-readable description of the scoring approach.
    """

    evaluator_names: tuple[str, ...]
    input_labels: tuple[str, ...]
    results: list[list[list[Evaluation]]]
    passed: bool
    criteria_message: str
    scoring_strategy: str


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
            f"At least {pct_str} of test-case inputs must pass on all evaluators. "
            f"Uses best-of-N-passes semantics (any single pass meeting criteria is sufficient)."
        )
    # Custom callable — use repr
    return f"Custom criteria: {repr(criteria)}"


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

_PIXIE_REPO_URL = "https://github.com/yiouli/pixie-qa"
_PIXIE_FEEDBACK_URL = "https://feedback.gopixie.ai"
_PIXIE_BRAND_ICON_URL = (
    "https://github.com/user-attachments/assets/76c18199-f00a-4fb3-a12f-ce6c173727af"
)


def _render_brand_header(command_args: str, timestamp: str) -> str:
    """Render the branded scorecard header and feedback modal."""
    h = html.escape
    return "\n".join(
        [
            '<section class="brand-header" aria-label="Pixie scorecard header">',
            '  <div class="brand-lockup">',
            '    <div class="brand-logo" aria-hidden="true">',
            '      <span class="brand-logo-fallback">P</span>',
            f'      <img src="{h(_PIXIE_BRAND_ICON_URL)}" alt="Pixie logo" loading="lazy" '
            'referrerpolicy="no-referrer">',
            "    </div>",
            '    <div class="brand-copy">',
            '      <p class="eyebrow">Pixie QA</p>',
            "      <h1>Pixie Test Scorecard</h1>",
            '      <p class="brand-description">'
            "Inspect your eval results, star the project, and share feedback directly "
            "from this report."
            "</p>",
            "    </div>",
            "  </div>",
            '  <div class="brand-actions">',
            '    <button type="button" class="action-btn action-btn-secondary" '
            'onclick="toggleFeedbackModal(true)">Share feedback</button>',
            f'    <a class="action-btn action-btn-primary" href="{h(_PIXIE_REPO_URL)}" '
            'target="_blank" rel="noreferrer">★ Star yiouli/pixie-qa</a>',
            "  </div>",
            "</section>",
            '<div id="feedback-modal" class="modal-backdrop" hidden>',
            '  <div class="modal-card" role="dialog" aria-modal="true" '
            'aria-labelledby="feedback-modal-title">',
            '    <button type="button" class="modal-close" aria-label="Close feedback form" '
            'onclick="toggleFeedbackModal(false)">×</button>',
            '    <h2 id="feedback-modal-title">Send feedback to Pixie</h2>',
            '    <p class="modal-description">'
            "Tell us what worked, what felt confusing, or attach text artifacts that help "
            "us improve the scorecard experience."
            "</p>",
            f'    <form class="feedback-form" action="{h(_PIXIE_FEEDBACK_URL)}" '
            'method="post" enctype="multipart/form-data" target="_blank">',
            '      <input type="hidden" name="source" value="pixie-scorecard">',
            f'      <input type="hidden" name="command_args" value="{h(command_args)}">',
            f'      <input type="hidden" name="generated_at" value="{h(timestamp)}">',
            '      <label class="field-label" for="feedback-text">Feedback</label>',
            '      <textarea id="feedback-text" name="feedback" rows="6" required '
            'placeholder="Share your feedback about Pixie, this scorecard, or your eval workflow..."></textarea>',
            '      <label class="field-label" for="feedback-email">Email (optional)</label>',
            '      <input id="feedback-email" name="email" type="email" '
            'placeholder="you@example.com">',
            '      <label class="field-label" for="feedback-attachments">'
            "Text attachments (optional)</label>",
            '      <input id="feedback-attachments" name="attachments" type="file" multiple '
            'accept=".txt,.md,.log,.json,text/plain">',
            '      <p class="form-note">Submitting opens a new tab and posts your feedback '
            f'to <code>{h(_PIXIE_FEEDBACK_URL)}</code>.</p>',
            '      <div class="modal-actions">',
            '        <button type="button" class="action-btn action-btn-secondary" '
            'onclick="toggleFeedbackModal(false)">Cancel</button>',
            '        <button type="submit" class="action-btn action-btn-primary">Submit feedback</button>',
            "      </div>",
            "    </form>",
            "  </div>",
            "</div>",
        ]
    )


def generate_scorecard_html(report: ScorecardReport) -> str:
    """Render a :class:`ScorecardReport` as a self-contained HTML page.

    The generated page uses inline CSS (no external dependencies) and
    includes tabbed views for multi-pass results.

    Args:
        report: The scorecard report to render.

    Returns:
        Complete HTML document as a string.
    """
    h = html.escape  # shorthand

    n_total = len(report.test_records)
    n_passed = sum(1 for t in report.test_records if t.status == "passed")

    ts = report.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

    parts: list[str] = []
    parts.append(_HTML_HEAD.replace("{{TITLE}}", f"Pixie Test Scorecard — {ts}"))
    parts.append(_render_brand_header(report.command_args, ts))

    # ── Overview section ──────────────────────────────────────────────
    parts.append('<div class="section">')
    parts.append("<h2>Test Run Overview</h2>")
    parts.append(
        '<p class="meta"><strong>Command:</strong> '
        f"<code>{h(report.command_args)}</code></p>"
    )
    parts.append(f'<p class="meta"><strong>Timestamp:</strong> {h(ts)}</p>')

    status_class = "pass" if n_passed == n_total else "fail"
    parts.append(
        f'<p class="summary {status_class}">' f"{n_passed}/{n_total} tests passed</p>"
    )

    # Test overview table
    parts.append('<table class="overview-table">')
    parts.append("<thead><tr><th>Test</th><th>Status</th></tr></thead><tbody>")
    for tr in report.test_records:
        badge = _status_badge(tr.status)
        parts.append(f"<tr><td>{h(tr.name)}</td><td>{badge}</td></tr>")
    parts.append("</tbody></table>")
    parts.append("</div>")  # end overview

    # ── Per-test scorecards ───────────────────────────────────────────
    for tr in report.test_records:
        parts.append('<div class="section test-section">')
        badge = _status_badge(tr.status)
        parts.append(f"<h2>{h(tr.name)} {badge}</h2>")

        if tr.message:
            parts.append(f'<pre class="error-msg">{h(tr.message)}</pre>')

        if not tr.asserts:
            parts.append(
                "<p><em>No assert_pass / assert_dataset_pass calls recorded.</em></p>"
            )
        else:
            for a_idx, ar in enumerate(tr.asserts, 1):
                parts.append('<div class="assert-card">')
                assert_badge = _status_badge("passed" if ar.passed else "failed")
                parts.append(f"<h3>Assertion #{a_idx} {assert_badge}</h3>")
                parts.append(
                    f'<p class="scoring-strategy">'
                    f"<strong>Scoring strategy:</strong> {h(ar.scoring_strategy)}</p>"
                )
                parts.append(
                    f'<p class="criteria-msg">'
                    f"<strong>Result:</strong> {h(ar.criteria_message)}</p>"
                )

                n_passes = len(ar.results)
                if n_passes <= 1:
                    # Single pass — render table directly
                    pass_results = ar.results[0] if ar.results else []
                    parts.append(
                        _render_pass_table(
                            pass_results, ar.evaluator_names, ar.input_labels
                        )
                    )
                else:
                    # Multiple passes — tabbed view
                    tab_group_id = f"test-{id(tr)}-assert-{a_idx}"
                    parts.append('<div class="tab-group">')
                    parts.append('<div class="tab-buttons">')
                    for p_idx in range(n_passes):
                        active = " active" if p_idx == 0 else ""
                        parts.append(
                            f'<button class="tab-btn{active}" '
                            f"onclick=\"switchTab('{tab_group_id}', {p_idx})\">"
                            f"Pass {p_idx + 1}</button>"
                        )
                    parts.append("</div>")  # tab-buttons

                    for p_idx, pass_results in enumerate(ar.results):
                        display = "block" if p_idx == 0 else "none"
                        parts.append(
                            f'<div class="tab-content" '
                            f'data-group="{tab_group_id}" '
                            f'data-idx="{p_idx}" '
                            f'style="display:{display}">'
                        )
                        parts.append(
                            _render_pass_table(
                                pass_results, ar.evaluator_names, ar.input_labels
                            )
                        )
                        parts.append("</div>")  # tab-content
                    parts.append("</div>")  # tab-group

                parts.append("</div>")  # assert-card

        parts.append("</div>")  # test-section

    parts.append(_HTML_FOOT)
    return "\n".join(parts)


def _render_pass_table(
    pass_results: list[list[Evaluation]],
    evaluator_names: tuple[str, ...],
    input_labels: tuple[str, ...],
) -> str:
    """Render the evaluator × input result table for a single pass."""
    h = html.escape
    lines: list[str] = []

    # Summary row: per-evaluator pass counts
    n_inputs = len(pass_results)
    n_evaluators = len(evaluator_names)

    lines.append('<table class="eval-summary">')
    lines.append("<thead><tr><th>Evaluator</th><th>Passed</th></tr></thead><tbody>")
    for e_idx, e_name in enumerate(evaluator_names):
        passed = sum(
            1
            for inp_evals in pass_results
            if e_idx < len(inp_evals) and inp_evals[e_idx].score >= 0.5
        )
        lines.append(f"<tr><td>{h(e_name)}</td>" f"<td>{passed}/{n_inputs}</td></tr>")
    lines.append("</tbody></table>")

    # Detail table: inputs × evaluators
    if n_evaluators > 0 and n_inputs > 0:
        lines.append('<table class="eval-detail">')
        lines.append("<thead><tr><th>Input</th>")
        for e_name in evaluator_names:
            lines.append(f"<th>{h(e_name)}</th>")
        lines.append("</tr></thead><tbody>")

        for i_idx, inp_evals in enumerate(pass_results):
            label = (
                input_labels[i_idx] if i_idx < len(input_labels) else f"#{i_idx + 1}"
            )
            lines.append(f"<tr><td class='input-label'>{h(label)}</td>")
            for e_idx in range(n_evaluators):
                if e_idx < len(inp_evals):
                    ev = inp_evals[e_idx]
                    cls = "score-pass" if ev.score >= 0.5 else "score-fail"
                    lines.append(
                        f'<td class="{cls}" title="{h(ev.reasoning)}">'
                        f"{ev.score:.2f}</td>"
                    )
                else:
                    lines.append("<td>—</td>")
            lines.append("</tr>")
        lines.append("</tbody></table>")

    return "\n".join(lines)


def _status_badge(status: str) -> str:
    """Return an HTML span badge for a test status."""
    if status == "passed":
        return '<span class="badge pass">PASS</span>'
    elif status == "failed":
        return '<span class="badge fail">FAIL</span>'
    else:
        return '<span class="badge error">ERROR</span>'


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


# ---------------------------------------------------------------------------
# HTML template fragments
# ---------------------------------------------------------------------------

_HTML_HEAD = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITLE}}</title>
<style>
  :root {
    --pass: #22c55e;
    --fail: #ef4444;
    --error: #f59e0b;
    --bg: #f8fafc;
    --card: #ffffff;
    --border: #e2e8f0;
    --text: #1e293b;
    --muted: #64748b;
    --brand: #7c3aed;
    --brand-dark: #0f172a;
    --brand-surface: #eef2ff;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
      Oxygen, Ubuntu, Cantarell, sans-serif;
    background: var(--bg); color: var(--text);
    padding: 2rem; line-height: 1.6;
  }
  body.modal-open { overflow: hidden; }
  h1 { margin-bottom: .5rem; font-size: 2rem; line-height: 1.15; }
  h2 { margin-bottom: 1rem; font-size: 1.25rem;
    border-bottom: 2px solid var(--border);
    padding-bottom: .5rem; }
  h3 { margin-bottom: .75rem; font-size: 1.1rem; }
  .brand-header {
    background: linear-gradient(135deg, rgba(124,58,237,.12), rgba(15,23,42,.98));
    color: #fff; border-radius: 16px; padding: 1.5rem;
    margin-bottom: 1.5rem; display: flex; gap: 1.5rem;
    align-items: center; justify-content: space-between;
    box-shadow: 0 20px 35px rgba(15,23,42,.16);
  }
  .brand-lockup { display: flex; align-items: center; gap: 1rem; }
  .brand-logo {
    position: relative; width: 72px; height: 72px; border-radius: 22px;
    background: linear-gradient(135deg, #8b5cf6, #0f172a);
    overflow: hidden; flex: 0 0 auto;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.12);
  }
  .brand-logo img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }
  .brand-logo-fallback {
    display: flex; align-items: center; justify-content: center; height: 100%;
    font-size: 2rem; font-weight: 800; letter-spacing: .06em;
  }
  .eyebrow {
    color: rgba(255,255,255,.74); text-transform: uppercase; letter-spacing: .14em;
    font-size: .78rem; font-weight: 700; margin-bottom: .35rem;
  }
  .brand-copy { max-width: 42rem; }
  .brand-description { color: rgba(255,255,255,.82); max-width: 44rem; }
  .brand-actions {
    display: flex; gap: .75rem; align-items: center; flex-wrap: wrap;
    justify-content: flex-end;
  }
  .action-btn {
    border: 0; border-radius: 999px; padding: .85rem 1.15rem;
    font-weight: 700; font-size: .95rem; text-decoration: none; cursor: pointer;
    display: inline-flex; align-items: center; justify-content: center;
    transition: transform .12s ease, box-shadow .12s ease, background .12s ease;
  }
  .action-btn:hover { transform: translateY(-1px); }
  .action-btn-primary {
    background: linear-gradient(135deg, #8b5cf6, #7c3aed); color: #fff;
    box-shadow: 0 10px 24px rgba(124,58,237,.28);
  }
  .action-btn-secondary {
    background: rgba(255,255,255,.1); color: #fff;
    border: 1px solid rgba(255,255,255,.18);
  }
  .section {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,.06);
  }
  .meta { color: var(--muted); margin-bottom: .5rem; }
  code { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: .9em; }
  .summary { font-size: 1.3rem; font-weight: 700; margin: 1rem 0; }
  .summary.pass { color: var(--pass); }
  .summary.fail { color: var(--fail); }
  .badge {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: .75rem; font-weight: 700; letter-spacing: .5px;
    color: #fff; vertical-align: middle;
  }
  .badge.pass { background: var(--pass); }
  .badge.fail { background: var(--fail); }
  .badge.error { background: var(--error); }
  table {
    width: 100%; border-collapse: collapse; margin: .75rem 0;
    font-size: .9rem;
  }
  th, td {
    padding: 8px 12px; text-align: left;
    border-bottom: 1px solid var(--border);
  }
  th { background: #f1f5f9; font-weight: 600; }
  .score-pass { color: var(--pass); font-weight: 600; }
  .score-fail { color: var(--fail); font-weight: 600; }
  .input-label { max-width: 300px; overflow: hidden;
    text-overflow: ellipsis; white-space: nowrap; }
  .assert-card {
    border: 1px solid var(--border); border-radius: 6px;
    padding: 1rem; margin: 1rem 0; background: #fafbfc;
  }
  .scoring-strategy { color: var(--muted); margin-bottom: .5rem; font-size: .9rem; }
  .criteria-msg { margin-bottom: .75rem; font-size: .9rem; }
  .error-msg {
    background: #fef2f2; color: var(--fail); padding: 1rem;
    border-radius: 6px; overflow-x: auto; font-size: .85rem;
    margin-bottom: 1rem; white-space: pre-wrap;
  }
  .tab-group { margin-top: .75rem; }
  .tab-buttons { display: flex; gap: 4px; margin-bottom: .5rem; }
  .tab-btn {
    padding: 6px 14px; border: 1px solid var(--border);
    background: var(--card); border-radius: 4px 4px 0 0;
    cursor: pointer; font-size: .85rem;
  }
  .tab-btn.active { background: #f1f5f9; font-weight: 600; border-bottom-color: #f1f5f9; }
  .tab-content { /* toggled via JS */ }
  .modal-backdrop {
    position: fixed; inset: 0; background: rgba(15,23,42,.6); z-index: 20;
    display: flex; align-items: center; justify-content: center; padding: 1.5rem;
  }
  .modal-card {
    position: relative; width: min(100%, 680px); max-height: 100%;
    overflow-y: auto; background: var(--card); border-radius: 16px;
    padding: 1.5rem; box-shadow: 0 24px 60px rgba(15,23,42,.28);
  }
  .modal-close {
    position: absolute; top: 1rem; right: 1rem; width: 2rem; height: 2rem;
    border: 0; border-radius: 999px; background: #e2e8f0; color: var(--text);
    cursor: pointer; font-size: 1.1rem; line-height: 1;
  }
  .modal-description, .form-note { color: var(--muted); margin-bottom: 1rem; }
  .feedback-form { display: grid; gap: .75rem; }
  .field-label { font-weight: 600; color: var(--text); }
  .feedback-form textarea,
  .feedback-form input[type="email"],
  .feedback-form input[type="file"] {
    width: 100%; border: 1px solid var(--border); border-radius: 10px;
    padding: .85rem 1rem; font: inherit; background: #fff;
  }
  .feedback-form textarea { min-height: 9rem; resize: vertical; }
  .modal-actions {
    display: flex; justify-content: flex-end; gap: .75rem; margin-top: .5rem;
    flex-wrap: wrap;
  }
  @media (max-width: 780px) {
    body { padding: 1rem; }
    .brand-header { flex-direction: column; align-items: flex-start; }
    .brand-lockup { align-items: flex-start; }
    .brand-actions, .modal-actions { width: 100%; justify-content: stretch; }
    .action-btn { width: 100%; }
    .input-label { max-width: 180px; }
  }
</style>
</head>
<body>
"""

_HTML_FOOT = """\
<script>
function switchTab(group, idx) {
  document.querySelectorAll('[data-group="' + group + '"]').forEach(function(el) {
    el.style.display = 'none';
  });
  var target = document.querySelector('[data-group="' + group + '"][data-idx="' + idx + '"]');
  if (target) target.style.display = 'block';
  // Update active button
  var btns = document.querySelectorAll('.tab-btn');
  btns.forEach(function(btn) {
    var oc = btn.getAttribute('onclick');
    if (oc && oc.indexOf("'" + group + "'") !== -1) {
      btn.classList.remove('active');
      if (btn.getAttribute('onclick').indexOf(', ' + idx + ')') !== -1) {
        btn.classList.add('active');
      }
    }
  });
}
function toggleFeedbackModal(open) {
  var modal = document.getElementById('feedback-modal');
  if (!modal) return;
  modal.hidden = !open;
  document.body.classList.toggle('modal-open', open);
}
document.addEventListener('keydown', function(event) {
  if (event.key === 'Escape') {
    toggleFeedbackModal(false);
  }
});
document.addEventListener('click', function(event) {
  var modal = document.getElementById('feedback-modal');
  if (modal && event.target === modal) {
    toggleFeedbackModal(false);
  }
});
</script>
</body>
</html>
"""
