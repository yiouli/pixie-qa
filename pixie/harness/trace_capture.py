"""Per-entry unified trace capture for ``pixie test``.

Provides :class:`EntryTraceCollector`, which collects **all** events for
each dataset entry — entry kwargs, ``wrap()`` emissions (input, output,
state), and ``LLMSpan`` objects — preserving chronological order.

A context variable (:data:`current_entry_index`) identifies which entry
the current async task belongs to, so concurrent entries are tracked
independently.

The companion :class:`EntryTraceLogProcessor` is an OTel
``LogRecordProcessor`` that intercepts ``wrap()`` emissions and routes
them to the active :class:`EntryTraceCollector`.

Usage::

    collector = EntryTraceCollector()
    set_active_collector(collector)
    add_handler(collector)

    log_processor = EntryTraceLogProcessor()
    logger_provider.add_log_record_processor(log_processor)

    current_entry_index.set(0)
    record_entry_kwargs(0, {"user_message": "hi"})
    # …run entry… (wrap events and LLM spans are captured automatically)
    count = collector.write_entry_trace(0, "/path/to/traces/entry-0.jsonl")
"""

from __future__ import annotations

import contextvars
import json
import os
import threading
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from opentelemetry.sdk._logs import LogRecordProcessor, ReadWriteLogRecord

from pixie.instrumentation.llm_tracing import InstrumentationHandler, LLMSpan
from pixie.instrumentation.models import EntryInputLog, LLMSpanTrace

current_entry_index: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "current_entry_index", default=None
)
"""Context variable set by the runner to identify the current dataset entry."""


# ── Module-level active collector ────────────────────────────────────────────

_active_collector: EntryTraceCollector | None = None


def set_active_collector(collector: EntryTraceCollector | None) -> None:
    """Set the module-level active :class:`EntryTraceCollector`."""
    global _active_collector  # noqa: PLW0603
    _active_collector = collector


def get_active_collector() -> EntryTraceCollector | None:
    """Return the active :class:`EntryTraceCollector`, or ``None``."""
    return _active_collector


def record_entry_kwargs(entry_index: int, kwargs: dict[str, Any]) -> None:
    """Store entry kwargs in the active collector for later trace writing.

    No-op if no collector is active.
    """
    if _active_collector is not None:
        _active_collector.set_entry_kwargs(entry_index, kwargs)


# ── EntryTraceCollector ──────────────────────────────────────────────────────


class EntryTraceCollector(InstrumentationHandler):
    """Collects entry kwargs, wrap events, and LLM spans per entry.

    Thread-safe: LLM spans arrive from the OTel delivery thread while
    wrap events arrive from the event loop thread.  The entry index is
    read from :data:`current_entry_index` at the time each event arrives;
    events without an entry context are silently dropped.
    """

    def __init__(self) -> None:
        self._entry_kwargs: dict[int, dict[str, Any]] = {}
        self._wrap_events: dict[int, list[dict[str, Any]]] = defaultdict(list)
        self._llm_spans: dict[int, list[LLMSpan]] = defaultdict(list)
        self._lock = threading.Lock()

    def set_entry_kwargs(self, entry_index: int, kwargs: dict[str, Any]) -> None:
        """Store the runnable kwargs for an entry."""
        with self._lock:
            self._entry_kwargs[entry_index] = kwargs

    def add_wrap_event(self, entry_index: int, body: dict[str, Any]) -> None:
        """Add a wrap event for an entry (called by :class:`EntryTraceLogProcessor`)."""
        with self._lock:
            self._wrap_events[entry_index].append(body)

    async def on_llm(self, span: LLMSpan) -> None:
        """Accumulate *span* under the current entry index."""
        entry_idx = current_entry_index.get()
        if entry_idx is None:
            return  # span outside entry context — drop silently
        with self._lock:
            self._llm_spans[entry_idx].append(span)

    def write_entry_trace(self, entry_index: int, output_path: str) -> int:
        """Write the full trace for *entry_index* to a JSONL file.

        The output contains, in chronological order:

        1. An ``EntryInputLog`` record with the entry kwargs.
        2. Interleaved wrap events and LLM span records, sorted by
           timestamp (``captured_at`` for wraps, ``started_at`` for spans).

        Creates parent directories if needed.

        Args:
            entry_index: The dataset entry index.
            output_path: Absolute path to the JSONL output file.

        Returns:
            The total number of records written (including kwargs).
        """
        with self._lock:
            kwargs = self._entry_kwargs.pop(entry_index, None)
            wrap_events = self._wrap_events.pop(entry_index, [])
            llm_spans = self._llm_spans.pop(entry_index, [])

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        count = 0
        with open(output_path, "w", encoding="utf-8") as f:
            # 1. Write entry kwargs
            if kwargs is not None:
                entry_log = EntryInputLog(value=kwargs)
                f.write(json.dumps(entry_log.model_dump(mode="json")) + "\n")
                count += 1

            # 2. Build timeline of wrap events and LLM spans
            timeline: list[tuple[str, dict[str, Any]]] = []

            for evt in wrap_events:
                ts = evt.get("captured_at", "")
                timeline.append((ts, evt))

            for span in llm_spans:
                trace_log = LLMSpanTrace(
                    operation=span.operation,
                    provider=span.provider,
                    request_model=span.request_model,
                    response_model=span.response_model,
                    input_tokens=span.input_tokens,
                    output_tokens=span.output_tokens,
                    duration_ms=span.duration_ms,
                    started_at=span.started_at.isoformat(),
                    ended_at=span.ended_at.isoformat(),
                    input_messages=[asdict(msg) for msg in span.input_messages],
                    output_messages=[
                        asdict(msg) for msg in span.output_messages
                    ],
                    tool_definitions=[
                        asdict(tool) for tool in span.tool_definitions
                    ],
                    finish_reasons=list(span.finish_reasons),
                    error_type=span.error_type,
                )
                timeline.append(
                    (span.started_at.isoformat(), trace_log.model_dump(mode="json"))
                )

            # Sort by timestamp for chronological order
            timeline.sort(key=lambda x: x[0])

            for _, record in timeline:
                f.write(json.dumps(record, default=str) + "\n")
                count += 1

        return count


# ── EntryTraceLogProcessor ───────────────────────────────────────────────────


class EntryTraceLogProcessor(LogRecordProcessor):
    """Route ``wrap()`` emissions to the active :class:`EntryTraceCollector`.

    Each wrap event is stamped with ``captured_at`` and filed under the
    current entry index (from :data:`current_entry_index`).  Events
    outside an entry context are silently dropped.
    """

    def on_emit(self, log_record: ReadWriteLogRecord) -> None:  # noqa: D102
        body = log_record.log_record.body
        if not isinstance(body, dict) or body.get("type") != "wrap":
            return

        entry_idx = current_entry_index.get()
        if entry_idx is None:
            return

        collector = get_active_collector()
        if collector is None:
            return

        # Stamp with capture time and route to collector
        body_copy = dict(body)
        body_copy["captured_at"] = datetime.now(timezone.utc).isoformat()
        collector.add_wrap_event(entry_idx, body_copy)

    def shutdown(self) -> None:  # noqa: D102
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:  # noqa: D102
        return True


# ── Backward compatibility ───────────────────────────────────────────────────

# Keep old name as alias for code that imports TraceCaptureHandler
TraceCaptureHandler = EntryTraceCollector
