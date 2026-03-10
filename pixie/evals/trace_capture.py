"""In-memory trace capture for eval test execution.

Provides ``MemoryTraceHandler`` that collects spans into a list, and a
``capture_traces`` context manager for scoped trace capture during tests.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

import pixie.instrumentation as px
from pixie.instrumentation.handler import InstrumentationHandler
from pixie.instrumentation.spans import LLMSpan, ObserveSpan
from pixie.storage.tree import ObservationNode, build_tree


class MemoryTraceHandler(InstrumentationHandler):
    """Collects ObserveSpan and LLMSpan instances into an in-memory list.

    Used by the eval test runner to capture traces without writing to disk.
    Implements the ``InstrumentationHandler`` interface so it integrates
    with the existing instrumentation pipeline.
    """

    def __init__(self) -> None:
        self.spans: list[ObserveSpan | LLMSpan] = []

    async def on_llm(self, span: LLMSpan) -> None:
        """Called when an LLM span completes."""
        self.spans.append(span)

    async def on_observe(self, span: ObserveSpan) -> None:
        """Called when an observe span completes."""
        self.spans.append(span)

    def get_trace(self, trace_id: str) -> list[ObservationNode]:
        """Filter spans by *trace_id* and build the tree."""
        matching = [s for s in self.spans if s.trace_id == trace_id]
        return build_tree(matching)

    def get_all_traces(self) -> dict[str, list[ObservationNode]]:
        """Group all captured spans by trace_id and build trees."""
        by_trace: dict[str, list[ObserveSpan | LLMSpan]] = {}
        for s in self.spans:
            by_trace.setdefault(s.trace_id, []).append(s)
        return {tid: build_tree(spans) for tid, spans in by_trace.items()}

    def clear(self) -> None:
        """Remove all collected spans."""
        self.spans.clear()


@contextmanager
def capture_traces() -> Generator[MemoryTraceHandler, None, None]:
    """Context manager that installs a ``MemoryTraceHandler`` and yields it.

    Calls ``init()`` (no-op if already initialised) then registers the
    handler via ``add_handler()``.  On exit the handler is removed and
    the delivery queue is flushed so that all spans are available on
    ``handler.spans``.
    """
    px.init()
    handler = MemoryTraceHandler()
    px.add_handler(handler)
    try:
        yield handler
    finally:
        px.flush()
        px.remove_handler(handler)
