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
