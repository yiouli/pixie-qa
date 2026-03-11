"""InstrumentationHandler base class and handler registry."""

from __future__ import annotations

import asyncio
import threading

from .spans import LLMSpan, ObserveSpan


class InstrumentationHandler:
    """Base class for instrumentation handlers.

    Both methods are optional async overrides — a handler only implementing
    on_llm is valid, and vice versa.  Implementations may be long-running
    (e.g. calling external APIs) since each handler coroutine runs
    concurrently with other registered handlers.
    """

    async def on_llm(self, span: LLMSpan) -> None:
        """Called when an LLM provider call completes.

        Default: no-op. Override to capture LLM call data for root-cause analysis.
        Exceptions are caught and suppressed.
        """

    async def on_observe(self, span: ObserveSpan) -> None:
        """Called when a log() block completes.

        Default: no-op. Override to capture eval-relevant data.
        Exceptions are caught and suppressed.
        """


class _HandlerRegistry(InstrumentationHandler):
    """Fan-out handler that dispatches to multiple registered handlers.

    Thread-safe: handlers can be added/removed from any thread.
    Each handler coroutine runs concurrently via ``asyncio.gather``;
    per-handler exceptions are isolated so one failing handler does not
    prevent delivery to the remaining handlers.
    """

    def __init__(self) -> None:
        self._handlers: list[InstrumentationHandler] = []
        self._lock = threading.Lock()

    def add(self, handler: InstrumentationHandler) -> None:
        """Register *handler* to receive span notifications."""
        with self._lock:
            self._handlers.append(handler)

    def remove(self, handler: InstrumentationHandler) -> None:
        """Unregister *handler*. Raises ``ValueError`` if not found."""
        with self._lock:
            self._handlers.remove(handler)

    async def on_llm(self, span: LLMSpan) -> None:
        """Dispatch to all registered handlers concurrently, isolating exceptions."""
        with self._lock:
            snapshot = list(self._handlers)
        await asyncio.gather(*(h.on_llm(span) for h in snapshot), return_exceptions=True)

    async def on_observe(self, span: ObserveSpan) -> None:
        """Dispatch to all registered handlers concurrently, isolating exceptions."""
        with self._lock:
            snapshot = list(self._handlers)
        await asyncio.gather(*(h.on_observe(span) for h in snapshot), return_exceptions=True)
