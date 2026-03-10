"""InstrumentationHandler base class and handler registry."""

from __future__ import annotations

import contextlib
import threading

from .spans import LLMSpan, ObserveSpan


class InstrumentationHandler:
    """Base class for instrumentation handlers.

    Both methods are optional overrides — a handler only implementing
    on_llm is valid, and vice versa.
    """

    def on_llm(self, span: LLMSpan) -> None:
        """Called on background thread when an LLM provider call completes.

        Default: no-op. Override to capture LLM call data for root-cause analysis.
        Exceptions are caught and suppressed.
        """

    def on_observe(self, span: ObserveSpan) -> None:
        """Called on background thread when a log() block completes.

        Default: no-op. Override to capture eval-relevant data.
        Exceptions are caught and suppressed.
        """


class _HandlerRegistry(InstrumentationHandler):
    """Fan-out handler that dispatches to multiple registered handlers.

    Thread-safe: handlers can be added/removed from any thread while the
    delivery worker calls ``on_llm``/``on_observe`` from the background
    thread.  Per-handler exceptions are caught so one failing handler
    does not prevent delivery to the remaining handlers.
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

    def on_llm(self, span: LLMSpan) -> None:
        """Dispatch to all registered handlers, isolating exceptions."""
        with self._lock:
            snapshot = list(self._handlers)
        for h in snapshot:
            with contextlib.suppress(Exception):
                h.on_llm(span)

    def on_observe(self, span: ObserveSpan) -> None:
        """Dispatch to all registered handlers, isolating exceptions."""
        with self._lock:
            snapshot = list(self._handlers)
        for h in snapshot:
            with contextlib.suppress(Exception):
                h.on_observe(span)
