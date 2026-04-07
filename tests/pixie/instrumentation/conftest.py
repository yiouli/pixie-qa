"""Shared fixtures for pixie instrumentation tests."""

from __future__ import annotations

import pytest

import pixie.instrumentation.observation as px
from pixie.instrumentation.handler import InstrumentationHandler
from pixie.instrumentation.spans import LLMSpan, ObserveSpan
from pixie.instrumentation.wrap_processors import ensure_eval_capture_registered

# Register a single EvalCaptureLogProcessor for all instrumentation tests.
# Uses a centralized guard to prevent duplicate registration across test
# modules (OTel processors are additive and cannot be removed).
ensure_eval_capture_registered()


class RecordingHandler(InstrumentationHandler):
    """Test handler that records all delivered spans."""

    def __init__(self) -> None:
        self.llm_spans: list[LLMSpan] = []
        self.observe_spans: list[ObserveSpan] = []

    async def on_llm(self, span: LLMSpan) -> None:
        self.llm_spans.append(span)

    async def on_observe(self, span: ObserveSpan) -> None:
        self.observe_spans.append(span)


@pytest.fixture
def recording_handler() -> RecordingHandler:
    """Provide a RecordingHandler that captures all spans."""
    return RecordingHandler()


@pytest.fixture(autouse=True)
def _reset_instrumentation() -> None:
    """Reset global instrumentation state before each test."""
    px._reset_state()
