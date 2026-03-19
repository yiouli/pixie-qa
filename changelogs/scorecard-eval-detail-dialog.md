# Scorecard: Evaluator cell "details" dialog

## What changed

Each evaluator score cell in the scorecard detail table now has a **"details"** hyperlink.
Clicking it opens a modal dialog showing:

- **Score** — numeric value with green ✓ or red ✗ indicator
- **Reasoning** — the full `Evaluation.reasoning` string (previously only shown as a tooltip)
- **Details** — the `Evaluation.details` dict rendered as pretty-printed JSON (hidden when empty)

The modal is dismiss-able via the **Close** button, the **Esc** key, or a click on the backdrop — consistent with the existing feedback modal.

## Files affected

- `pixie/evals/scorecard.py`
  - Added `import json`
  - New `_render_eval_detail_modal()` helper — renders the reusable hidden modal
  - `generate_scorecard_html()` — calls `_render_eval_detail_modal()` after the brand header
  - `_render_pass_table()` — each evaluator cell now embeds a `data-eval` JSON attribute and a `details` link
  - `_HTML_HEAD` — added CSS for `.details-link`, `.eval-detail-body`, `.eval-detail-row`, `.eval-detail-label`, `.eval-detail-value`, `.eval-detail-score-pass/fail`, `.eval-detail-json`
  - `_HTML_FOOT` — added `showEvalDetail(link)` and `closeEvalDetailModal()` JS functions; updated Esc and backdrop-click handlers to also close the eval-detail modal

## Migration notes

No API changes. The `AssertRecord`, `Evaluation`, and `ScorecardReport` models are unchanged.
Existing scorecards already stored `Evaluation.reasoning` as a cell `title` attribute (tooltip);
that attribute has been replaced by the clickable details link — tooltip-only access is no longer available.
