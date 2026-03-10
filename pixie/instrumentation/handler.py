"""InstrumentationHandler base class."""

from __future__ import annotations

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
