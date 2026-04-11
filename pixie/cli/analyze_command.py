"""``pixie analyze`` CLI command.

Generates deterministic analysis of test run results: per-evaluator
statistics, failure clusters, trace summaries, and cross-dataset patterns.
No LLM calls, no API keys — all computation is from the test result data.

Usage::

    pixie analyze <test_run_id>

Output is saved alongside the result JSON at
``<pixie_root>/results/<test_id>/dataset-<index>.md`` and
``<pixie_root>/results/<test_id>/summary.md``.
"""

from __future__ import annotations

import json
import os
import statistics
from collections import defaultdict
from typing import Any

from pixie.harness.run_result import (
    DatasetResult,
    EntryResult,
    EvaluationResult,
    RunResult,
    load_test_result,
)
from pixie.instrumentation.models import LLMSpanTrace

# ── Trace loading ─────────────────────────────────────────────────────────────


def _load_full_trace(result_dir: str, entry: EntryResult) -> list[dict[str, Any]]:
    """Load all trace records for an entry from its JSONL file.

    Returns a list of raw dicts preserving the original chronological
    order (entry kwargs first, then interleaved wrap events and LLM spans).
    Returns an empty list if no trace file exists or if parsing fails.
    """
    if entry.trace_file is None:
        return []
    trace_path = os.path.join(result_dir, entry.trace_file)
    if not os.path.isfile(trace_path):
        return []
    records: list[dict[str, Any]] = []
    with open(trace_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue  # Skip malformed lines.
    return records


def _load_entry_traces(result_dir: str, entry: EntryResult) -> list[LLMSpanTrace]:
    """Load LLM span trace records for an entry.

    Filters the full trace to only ``llm_span_trace`` records (and legacy
    ``llm_span`` records for backward compatibility).
    Returns an empty list if no trace file exists.
    """
    records = _load_full_trace(result_dir, entry)
    traces: list[LLMSpanTrace] = []
    for r in records:
        rtype = r.get("type")
        if rtype in ("llm_span_trace", "llm_span"):
            try:
                traces.append(LLMSpanTrace.model_validate(r))
            except Exception:
                continue
    return traces


def _completed_evals(entry: EntryResult) -> list[EvaluationResult]:
    """Return only completed evaluations, filtering out pending ones."""
    return [ev for ev in entry.evaluations if isinstance(ev, EvaluationResult)]


# ── Statistics helpers ────────────────────────────────────────────────────────


def _evaluator_stats(
    ds: DatasetResult,
) -> dict[str, dict[str, float | str]]:
    """Compute per-evaluator statistics for a dataset.

    Returns a dict mapping evaluator name to a stats dict with keys:
    pass_rate, min, max, mean, stddev.
    """
    scores_by_evaluator: dict[str, list[float]] = defaultdict(list)
    for entry in ds.entries:
        for ev in _completed_evals(entry):
            scores_by_evaluator[ev.evaluator].append(ev.score)

    result: dict[str, dict[str, float | str]] = {}
    for name, scores in scores_by_evaluator.items():
        passed = sum(1 for s in scores if s >= 0.5)
        pass_rate = passed / len(scores) * 100 if scores else 0.0
        mean = statistics.mean(scores) if scores else 0.0
        stddev = statistics.stdev(scores) if len(scores) >= 2 else 0.0
        result[name] = {
            "pass_rate": round(pass_rate, 1),
            "min": round(min(scores), 2) if scores else 0.0,
            "max": round(max(scores), 2) if scores else 0.0,
            "mean": round(mean, 2),
            "stddev": round(stddev, 2),
        }
    return result


def _failure_clusters(
    ds: DatasetResult,
) -> dict[str, list[tuple[int, EntryResult]]]:
    """Group failing entries by their set of failed evaluators.

    Returns a dict mapping a sorted comma-separated evaluator set string
    to a list of (entry_index, EntryResult) tuples.
    """
    clusters: dict[str, list[tuple[int, EntryResult]]] = defaultdict(list)
    for i, entry in enumerate(ds.entries):
        failed_evals = sorted(
            ev.evaluator for ev in _completed_evals(entry) if ev.score < 0.5
        )
        if failed_evals:
            key = ", ".join(failed_evals)
            clusters[key].append((i, entry))
    return dict(clusters)


# ── Markdown builders ─────────────────────────────────────────────────────────


def _build_dataset_summary(
    ds: DatasetResult,
    result_dir: str,
) -> str:
    """Build the deterministic analysis markdown for a single dataset.

    Includes: Overview, Per-Evaluator Statistics, Failure Clusters,
    Trace Summary (when available), and Entry Details.
    """
    lines: list[str] = []
    total = len(ds.entries)
    passed = sum(
        1 for e in ds.entries if all(ev.score >= 0.5 for ev in _completed_evals(e))
    )
    failed = total - passed
    rate = passed / total * 100 if total else 0.0

    # Overview
    lines.append(f"# Dataset: {ds.dataset}")
    lines.append("")
    lines.append("## Overview")
    lines.append(f"- **Entries**: {total} ({passed} passed, {failed} failed)")
    lines.append(f"- **Pass rate**: {rate:.1f}%")
    lines.append("")

    # Per-Evaluator Statistics
    stats = _evaluator_stats(ds)
    if stats:
        lines.append("## Per-Evaluator Statistics")
        lines.append("")
        lines.append("| Evaluator | Pass Rate | Min | Max | Mean | Stddev |")
        lines.append("|-----------|-----------|-----|-----|------|--------|")
        for name, s in stats.items():
            lines.append(
                f"| {name} | {s['pass_rate']}% | {s['min']} | {s['max']} "
                f"| {s['mean']} | {s['stddev']} |"
            )
        lines.append("")

    # Failure Clusters
    clusters = _failure_clusters(ds)
    if clusters:
        lines.append("## Failure Clusters")
        lines.append("")
        for eval_set, entries in clusters.items():
            lines.append(f"### Cluster: {eval_set}")
            lines.append(f"Entries failing: {eval_set}")
            lines.append("")
            lines.append("| Entry | Description | Scores | Reasoning |")
            lines.append("|-------|-------------|--------|-----------|")
            for idx, entry in entries:
                desc = entry.description or str(entry.input)
                if len(desc) > 60:
                    desc = desc[:60] + "…"
                scores_str = ", ".join(
                    f"{ev.evaluator}={ev.score:.2f}" for ev in _completed_evals(entry)
                )
                reasoning_str = "; ".join(
                    f"{ev.evaluator}: {ev.reasoning}"
                    for ev in _completed_evals(entry)
                    if ev.score < 0.5
                )
                lines.append(f"| {idx} | {desc} | {scores_str} | {reasoning_str} |")
            lines.append("")

    # Trace Summary
    has_traces = any(e.trace_file is not None for e in ds.entries)
    if has_traces:
        lines.append("## Trace Summary")
        lines.append("")
        lines.append(
            "| Entry | Models | Input Tokens | Output Tokens "
            "| Duration (ms) | Errors |"
        )
        lines.append(
            "|-------|--------|--------------|---------------"
            "|---------------|--------|"
        )
        for i, entry in enumerate(ds.entries):
            traces = _load_entry_traces(result_dir, entry)
            if not traces:
                lines.append(f"| {i} | — | 0 | 0 | 0 | — |")
                continue
            models = sorted({t.request_model or "?" for t in traces})
            in_tok = sum(t.input_tokens for t in traces)
            out_tok = sum(t.output_tokens for t in traces)
            dur = sum(t.duration_ms for t in traces)
            errors = [t.error_type for t in traces if t.error_type]
            err_str = ", ".join(errors) if errors else "—"
            lines.append(
                f"| {i} | {', '.join(models)} | {in_tok} | {out_tok} "
                f"| {dur:.0f} | {err_str} |"
            )
        lines.append("")

    # Entry Details
    lines.append("## Entry Details")
    lines.append("")
    for i, entry in enumerate(ds.entries):
        desc = entry.description or str(entry.input)
        all_pass = all(ev.score >= 0.5 for ev in _completed_evals(entry))
        status = "PASS" if all_pass else "FAIL"
        lines.append(f"### Entry {i}: {desc}")
        lines.append(f"- **Status**: {status}")
        lines.append(f"- **Input**: {json.dumps(entry.input)}")
        lines.append(f"- **Output**: {json.dumps(entry.output)}")
        if entry.expected_output is not None:
            lines.append(f"- **Expected**: {json.dumps(entry.expected_output)}")
        lines.append("")
        lines.append("| Evaluator | Score | Pass | Reasoning |")
        lines.append("|-----------|-------|------|-----------|")
        for ev in _completed_evals(entry):
            pass_str = "PASS" if ev.score >= 0.5 else "FAIL"
            lines.append(
                f"| {ev.evaluator} | {ev.score:.2f} | {pass_str} | {ev.reasoning} |"
            )
        lines.append("")

        # Per-entry trace details
        if has_traces:
            full_trace = _load_full_trace(result_dir, entry)
            llm_records = [
                r for r in full_trace if r.get("type") in ("llm_span_trace", "llm_span")
            ]
            wrap_events = [r for r in full_trace if r.get("type") == "wrap"]
            event_count = len(wrap_events) + len(llm_records)
            if full_trace:
                lines.append(
                    f"**Trace** ({event_count} events: "
                    f"{len(wrap_events)} wrap, {len(llm_records)} LLM):"
                )
                lines.append("")
                lines.append("| # | Type | Name / Model | Detail |")
                lines.append("|---|------|-------------|--------|")
                step = 0
                for rec in full_trace:
                    rtype = rec.get("type", "")
                    if rtype == "kwargs":
                        continue  # kwargs are shown in Input above
                    if rtype == "wrap":
                        name = rec.get("name", "?")
                        purpose = rec.get("purpose", "?")
                        lines.append(f"| {step} | wrap({purpose}) | {name} | — |")
                        step += 1
                    elif rtype in ("llm_span_trace", "llm_span"):
                        model = rec.get("request_model") or "?"
                        in_tok = rec.get("input_tokens", 0)
                        out_tok = rec.get("output_tokens", 0)
                        dur = rec.get("duration_ms", 0)
                        err = rec.get("error_type") or "—"
                        lines.append(
                            f"| {step} | llm | {model} "
                            f"| {in_tok}/{out_tok} tok, "
                            f"{dur:.0f}ms, err={err} |"
                        )
                        step += 1
                lines.append("")

    return "\n".join(lines)


def _build_cross_dataset_summary(result: RunResult, result_dir: str) -> str:
    """Build cross-dataset summary markdown.

    Includes aggregate statistics, evaluator consistency, common failure
    patterns, and aggregate trace statistics.
    """
    lines: list[str] = []
    total_entries = sum(len(ds.entries) for ds in result.datasets)
    total_passed = sum(
        1
        for ds in result.datasets
        for e in ds.entries
        if all(ev.score >= 0.5 for ev in _completed_evals(e))
    )
    overall_rate = total_passed / total_entries * 100 if total_entries else 0.0

    lines.append("# Cross-Dataset Summary")
    lines.append("")
    lines.append("## Aggregate Statistics")
    lines.append(
        f"- **Total entries**: {total_entries} across {len(result.datasets)} dataset(s)"
    )
    lines.append(f"- **Overall pass rate**: {overall_rate:.1f}%")
    lines.append("")

    # Evaluator Consistency
    evaluator_datasets: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for ds in result.datasets:
        stats = _evaluator_stats(ds)
        for name, s in stats.items():
            rate = s["pass_rate"]
            assert isinstance(rate, float)
            evaluator_datasets[name].append((ds.dataset, rate))

    if evaluator_datasets:
        lines.append("## Evaluator Consistency")
        lines.append("")
        lines.append(
            "| Evaluator | Datasets Used | Overall Pass Rate "
            "| Min Dataset Rate | Max Dataset Rate |"
        )
        lines.append(
            "|-----------|---------------|-------------------"
            "|------------------|------------------|"
        )
        for name, ds_rates in evaluator_datasets.items():
            rates = [r for _, r in ds_rates]
            ds_count = len(ds_rates)
            overall = statistics.mean(rates) if rates else 0.0
            min_r = min(rates) if rates else 0.0
            max_r = max(rates) if rates else 0.0
            lines.append(
                f"| {name} | {ds_count} | {overall:.1f}% "
                f"| {min_r:.1f}% | {max_r:.1f}% |"
            )
        lines.append("")

    # Common Failure Patterns
    all_clusters: dict[str, int] = defaultdict(int)
    for ds in result.datasets:
        clusters = _failure_clusters(ds)
        for eval_set, entries in clusters.items():
            all_clusters[eval_set] += len(entries)

    if all_clusters:
        lines.append("## Common Failure Patterns")
        lines.append("")
        for eval_set, count in sorted(all_clusters.items(), key=lambda x: -x[1]):
            lines.append(f"- **{eval_set}**: {count} entries across datasets")
        lines.append("")

    # Aggregate Trace Statistics
    total_calls = 0
    all_models: set[str] = set()
    total_in_tok = 0
    total_out_tok = 0
    total_latency = 0.0

    for ds in result.datasets:
        for entry in ds.entries:
            traces = _load_entry_traces(result_dir, entry)
            total_calls += len(traces)
            for t in traces:
                if t.request_model:
                    all_models.add(t.request_model)
                total_in_tok += t.input_tokens
                total_out_tok += t.output_tokens
                total_latency += t.duration_ms

    if total_calls > 0:
        lines.append("## Aggregate Trace Statistics")
        lines.append(f"- **Total LLM calls**: {total_calls}")
        lines.append(f"- **Models used**: {', '.join(sorted(all_models))}")
        lines.append(
            f"- **Total tokens**: {total_in_tok} input, {total_out_tok} output"
        )
        lines.append(f"- **Total latency**: {total_latency:.0f} ms")
        lines.append("")
    elif len(result.datasets) == 1:
        lines.append("*1 dataset — no cross-dataset patterns to report.*")
        lines.append("")

    return "\n".join(lines)


# ── Analysis orchestration ────────────────────────────────────────────────────


def _analyze_dataset(ds: DatasetResult, index: int, result_dir: str) -> str:
    """Generate deterministic analysis for a single dataset and save markdown.

    Args:
        ds: The dataset result to analyze.
        index: The dataset index (for the output filename).
        result_dir: Directory to save the analysis markdown.

    Returns:
        The generated analysis markdown content.
    """
    content = _build_dataset_summary(ds, result_dir)

    analysis_path = os.path.join(result_dir, f"dataset-{index}.md")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write(content)

    return content


def analyze(test_id: str) -> int:
    """Entry point for ``pixie analyze <test_run_id>``.

    Generates deterministic analysis markdown for each dataset and a
    cross-dataset summary.  No LLM calls, no API keys required.

    Args:
        test_id: The test run identifier to analyze.

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    try:
        result = load_test_result(test_id)
    except FileNotFoundError:
        print(f"Error: No test result found for ID {test_id!r}")  # noqa: T201
        return 1

    from pixie.config import get_config

    config = get_config()
    result_dir = os.path.join(config.root, "results", test_id)

    print(  # noqa: T201
        f"Analyzing {len(result.datasets)} dataset(s) for test run {test_id}..."
    )

    for i, ds in enumerate(result.datasets):
        _analyze_dataset(ds, i, result_dir)

    # Cross-dataset summary
    summary_content = _build_cross_dataset_summary(result, result_dir)
    summary_path = os.path.join(result_dir, "summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_content)

    print(f"Analysis saved to {result_dir}")  # noqa: T201
    return 0
