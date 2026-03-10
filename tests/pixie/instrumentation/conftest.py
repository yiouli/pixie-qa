"""Shared fixtures for pixie instrumentation tests."""

from __future__ import annotations

import pytest

from pixie.instrumentation.handler import InstrumentationHandler
from pixie.instrumentation.spans import LLMSpan, ObserveSpan


class RecordingHandler(InstrumentationHandler):
    """Test handler that records all delivered spans."""

    def __init__(self) -> None:
        self.llm_spans: list[LLMSpan] = []
        self.observe_spans: list[ObserveSpan] = []

    def on_llm(self, span: LLMSpan) -> None:
        self.llm_spans.append(span)

    def on_observe(self, span: ObserveSpan) -> None:
        self.observe_spans.append(span)


@pytest.fixture
def recording_handler() -> RecordingHandler:
    """Provide a RecordingHandler that captures all spans."""
    return RecordingHandler()
