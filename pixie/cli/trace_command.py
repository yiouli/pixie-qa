"""``pixie trace`` CLI subcommands — list, show, and last.

Provides read-only inspection of captured traces via the
:class:`~pixie.storage.store.ObservationStore`.

Commands::

    pixie trace list [--limit N] [--errors]
    pixie trace show <trace_id> [-v | --verbose] [--json]
    pixie trace last [--json]
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from piccolo.engine.sqlite import SQLiteEngine

from pixie.config import get_config
from pixie.storage.store import ObservationStore
from pixie.storage.tree import ObservationNode


def _make_store() -> ObservationStore:
    """Create an ObservationStore from config."""
    config = get_config()
    engine = SQLiteEngine(path=config.db_path)
    return ObservationStore(engine=engine)


def _format_datetime(value: Any) -> str:
    """Format a datetime value to a human-readable string."""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            return str(value)
    return str(value) if value is not None else ""


async def _trace_list(limit: int, errors_only: bool) -> list[dict[str, Any]]:
    """Fetch trace summaries from the store."""
    store = _make_store()
    traces = await store.list_traces(limit=limit)
    if errors_only:
        traces = [t for t in traces if t.get("has_error")]
    return traces


async def _trace_show(
    trace_id: str,
    verbose: bool,
    as_json: bool,
) -> str:
    """Fetch and render a single trace."""
    store = _make_store()
    # Support prefix matching
    traces = await store.list_traces(limit=500)
    matched = [t for t in traces if t["trace_id"].startswith(trace_id)]
    if not matched:
        return f"Error: No trace found matching '{trace_id}'"
    if len(matched) > 1:
        ids = "\n  ".join(t["trace_id"] for t in matched[:10])
        return f"Error: Multiple traces match '{trace_id}'. Be more specific:\n  {ids}"
    full_id = matched[0]["trace_id"]

    tree = await store.get_trace(full_id)
    if not tree:
        return f"Error: No spans found for trace '{full_id}'"

    if as_json:
        spans_data = []
        for node in tree:
            spans_data.extend(_collect_serialized(node))
        return json.dumps(spans_data, indent=2, default=str)

    # Text rendering — to_text already handles both compact and verbose
    # For compact mode, we use a stripped-down version
    if verbose:
        lines = [f"[trace_id: {full_id}]\n"]
        for root_node in tree:
            lines.append(root_node.to_text(indent=0))
        return "\n".join(lines)

    # Compact mode: just names and timing
    lines = [f"[trace_id: {full_id}]\n"]
    for root_node in tree:
        lines.append(_compact_text(root_node, indent=0))
    return "\n".join(lines)


async def _trace_last(as_json: bool) -> str:
    """Show the most recent trace in verbose mode."""
    store = _make_store()
    traces = await store.list_traces(limit=1)
    if not traces:
        return "No traces found."
    trace_id = traces[0]["trace_id"]
    return await _trace_show(trace_id, verbose=True, as_json=as_json)


def _compact_text(node: ObservationNode, indent: int = 0) -> str:
    """Render a compact text view (names and timing only)."""
    from pixie.instrumentation.spans import LLMSpan

    prefix = "  " * indent
    lines: list[str] = []
    if isinstance(node.span, LLMSpan):
        span = node.span
        header = (
            f"{prefix}{span.request_model} [{span.provider}, {span.duration_ms:.0f}ms]"
        )
        lines.append(header)
        token_parts: list[str] = []
        if span.input_tokens > 0 or span.output_tokens > 0:
            token_parts.append(f"{span.input_tokens} in / {span.output_tokens} out")
            lines.append(f"{prefix}  tokens: {' '.join(token_parts)}")
    else:
        name = node.span.name or "(unnamed)"
        lines.append(f"{prefix}{name} [{node.span.duration_ms:.0f}ms]")

    for child in node.children:
        lines.append(_compact_text(child, indent + 1))
    return "\n".join(lines)


def _collect_serialized(node: ObservationNode) -> list[dict[str, Any]]:
    """Recursively collect serialized spans from a tree."""
    from pixie.storage.serialization import serialize_span

    result: list[dict[str, Any]] = [serialize_span(node.span)]
    for child in node.children:
        result.extend(_collect_serialized(child))
    return result


def trace_list(limit: int = 10, errors_only: bool = False) -> int:
    """Entry point for ``pixie trace list``."""
    traces = asyncio.run(_trace_list(limit, errors_only))
    if not traces:
        print("No traces found.")  # noqa: T201
        return 0

    # Table header
    header = (
        f"{'TRACE_ID':<34}"
        f"{'ROOT SPAN':<25}"
        f"{'STARTED':<20}"
        f"{'SPANS':>6}"
        f"{'ERRORS':>7}"
    )
    print(header)  # noqa: T201
    for t in traces:
        row = (
            f"{t['trace_id']:<34}"
            f"{(t.get('root_name') or '(unknown)'):<25}"
            f"{_format_datetime(t.get('started_at')):<20}"
            f"{t.get('observation_count', 0):>6}"
            f"{('yes' if t.get('has_error') else ''):>7}"
        )
        print(row)  # noqa: T201
    return 0


def trace_show(
    trace_id: str,
    verbose: bool = False,
    as_json: bool = False,
) -> int:
    """Entry point for ``pixie trace show``."""
    output = asyncio.run(_trace_show(trace_id, verbose, as_json))
    print(output)  # noqa: T201
    return 1 if output.startswith("Error:") else 0


def trace_last(as_json: bool = False) -> int:
    """Entry point for ``pixie trace last``."""
    output = asyncio.run(_trace_last(as_json))
    print(output)  # noqa: T201
    return 0


# ── trace verify ──────────────────────────────────────────────────────────


async def _trace_verify() -> tuple[int, str]:
    """Verify the most recent trace for common instrumentation issues.

    Returns (exit_code, message) where exit_code is 0 if all checks pass.
    """
    store = _make_store()
    traces = await store.list_traces(limit=1)
    if not traces:
        return 1, "ERROR: No traces found. Run the app first to produce a trace."

    trace_id = traces[0]["trace_id"]
    tree = await store.get_trace(trace_id)
    if not tree:
        return 1, f"ERROR: No spans found for trace '{trace_id}'."

    lines: list[str] = []
    issues: list[str] = []

    lines.append(f"Trace: {trace_id}")
    lines.append(f"Spans: {_count_nodes(tree)}")
    lines.append("")

    # Check 1: Root span should be an @observe span, not an LLM span
    from pixie.instrumentation.spans import LLMSpan as _LLMSpan

    root_node = tree[0]
    root_is_llm = isinstance(root_node.span, _LLMSpan)
    if root_is_llm:
        issues.append(
            "Root span is an LLM call, not an @observe-decorated function. "
            "Ensure enable_storage() is called BEFORE the @observe function runs."
        )
        lines.append(f"Root span: {root_node.name} (LLM) <- WRONG")
    else:
        lines.append(f"Root span: {root_node.name} (observe) <- OK")

    # Check 2: Root span has input and output
    if not root_is_llm:
        root_observe = root_node.span
        has_input = getattr(root_observe, "input", None) is not None
        has_output = getattr(root_observe, "output", None) is not None
        if not has_input:
            issues.append(
                "Root span input is null. The @observe-decorated function's "
                "arguments are not being captured."
            )
            lines.append("Root input:  null <- MISSING")
        else:
            lines.append("Root input:  present <- OK")
        if not has_output:
            issues.append(
                "Root span output is null. The @observe-decorated function's "
                "return value is not being captured."
            )
            lines.append("Root output: null <- MISSING")
        else:
            lines.append("Root output: present <- OK")

    # Check 3: LLM child spans are present
    llm_count = 0
    for root in tree:
        llm_count += len(root.find_by_type(_LLMSpan))
    if llm_count == 0:
        issues.append(
            "No LLM child spans found. Ensure enable_storage() is called "
            "so that LLM provider calls (OpenAI, Anthropic) are auto-captured."
        )
        lines.append("LLM spans:   0 <- MISSING")
    else:
        lines.append(f"LLM spans:   {llm_count} <- OK")

    lines.append("")

    # Compact tree view
    lines.append("Span tree:")
    for root in tree:
        lines.append(_compact_text(root, indent=1))

    lines.append("")

    if issues:
        lines.append(f"FAILED — {len(issues)} issue(s):")
        for i, issue in enumerate(issues, 1):
            lines.append(f"  {i}. {issue}")
        return 1, "\n".join(lines)

    lines.append("PASSED — trace looks good.")
    return 0, "\n".join(lines)


def _count_nodes(tree: list[ObservationNode]) -> int:
    """Count total nodes in a tree."""
    count = 0
    for node in tree:
        count += 1 + _count_nodes(node.children)
    return count


def trace_verify() -> int:
    """Entry point for ``pixie trace verify``."""
    exit_code, output = asyncio.run(_trace_verify())
    print(output)  # noqa: T201
    return exit_code


# ── trace filter ──────────────────────────────────────────────────────────


def trace_filter(trace_file: str, purposes: list[str]) -> int:
    """Entry point for ``pixie trace filter``.

    Reads a JSONL trace file and outputs only lines whose ``purpose`` field
    matches one of the specified values.

    Args:
        trace_file: Path to the JSONL trace file.
        purposes: List of purpose values to include (e.g. ``["entry", "input"]``).

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    import sys
    from pathlib import Path

    path = Path(trace_file)
    if not path.exists():
        print(f"Error: File not found: {trace_file}", file=sys.stderr)  # noqa: T201
        return 1

    purpose_set = {p.strip() for p in purposes}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("purpose") in purpose_set:
                    print(line)  # noqa: T201
    except OSError as exc:
        print(f"Error reading {trace_file}: {exc}", file=sys.stderr)  # noqa: T201
        return 1

    return 0
