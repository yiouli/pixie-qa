"""Tests for pixie.instrumentation.handler — _HandlerRegistry concurrency and isolation."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from pixie.instrumentation.llm_tracing import InstrumentationHandler, _HandlerRegistry
from pixie.instrumentation.llm_tracing import LLMSpan, ObserveSpan


def _make_observe_span(name: str = "test") -> ObserveSpan:
    now = datetime.now(tz=timezone.utc)
    return ObserveSpan(
        span_id="0000000000000001",
        trace_id="00000000000000000000000000000001",
        parent_span_id=None,
        started_at=now,
        ended_at=now,
        duration_ms=0.0,
        name=name,
        input=None,
        output=None,
        metadata={},
        error=None,
    )


def _make_llm_span() -> LLMSpan:
    now = datetime.now(tz=timezone.utc)
    return LLMSpan(
        span_id="0000000000000002",
        trace_id="00000000000000000000000000000001",
        parent_span_id=None,
        started_at=now,
        ended_at=now,
        duration_ms=0.0,
        operation="chat",
        provider="openai",
        request_model="gpt-4",
        response_model=None,
        input_tokens=0,
        output_tokens=0,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        request_temperature=None,
        request_max_tokens=None,
        request_top_p=None,
        finish_reasons=(),
        response_id=None,
        output_type=None,
        error_type=None,
        input_messages=(),
        output_messages=(),
        tool_definitions=(),
    )


class TestHandlerRegistryConcurrency:
    """Tests that _HandlerRegistry dispatches all handlers concurrently."""

    def test_on_observe_handlers_run_concurrently(self) -> None:
        """Handlers for a single span run concurrently via asyncio.gather.

        If dispatch were sequential, the slow handler would finish before the
        fast handler even starts.  With concurrent dispatch the fast handler
        runs while the slow one is still awaiting its sleep, so the timeline
        shows interleaving.
        """
        timeline: list[str] = []

        class SlowHandler(InstrumentationHandler):
            async def on_observe(self, span: ObserveSpan) -> None:
                timeline.append("slow_start")
                await asyncio.sleep(0.05)
                timeline.append("slow_end")

        class FastHandler(InstrumentationHandler):
            async def on_observe(self, span: ObserveSpan) -> None:
                timeline.append("fast")

        registry = _HandlerRegistry()
        registry.add(SlowHandler())
        registry.add(FastHandler())

        asyncio.run(registry.on_observe(_make_observe_span()))

        # Sequential order would be: ["slow_start", "slow_end", "fast"]
        # Concurrent order must be:  ["slow_start", "fast", "slow_end"]
        assert timeline == [
            "slow_start",
            "fast",
            "slow_end",
        ], f"handlers did not run concurrently; got {timeline}"

    def test_on_llm_handlers_run_concurrently(self) -> None:
        """Same concurrency guarantee for on_llm dispatch."""
        timeline: list[str] = []

        class SlowHandler(InstrumentationHandler):
            async def on_llm(self, span: LLMSpan) -> None:
                timeline.append("slow_start")
                await asyncio.sleep(0.05)
                timeline.append("slow_end")

        class FastHandler(InstrumentationHandler):
            async def on_llm(self, span: LLMSpan) -> None:
                timeline.append("fast")

        registry = _HandlerRegistry()
        registry.add(SlowHandler())
        registry.add(FastHandler())

        asyncio.run(registry.on_llm(_make_llm_span()))

        assert timeline == [
            "slow_start",
            "fast",
            "slow_end",
        ], f"on_llm handlers did not run concurrently; got {timeline}"


class TestHandlerRegistryErrorIsolation:
    """Tests that an exception in one handler does not prevent others from running."""

    def test_raising_on_observe_does_not_block_other_handlers(self) -> None:
        """A handler that raises must not prevent subsequent handlers from receiving the span."""
        received: list[str] = []

        class RaisingHandler(InstrumentationHandler):
            async def on_observe(self, span: ObserveSpan) -> None:
                raise RuntimeError("intentional crash")

        class GoodHandler(InstrumentationHandler):
            async def on_observe(self, span: ObserveSpan) -> None:
                received.append("ok")

        registry = _HandlerRegistry()
        registry.add(RaisingHandler())
        registry.add(GoodHandler())

        # Must not raise itself
        asyncio.run(registry.on_observe(_make_observe_span()))

        assert received == ["ok"]

    def test_raising_on_llm_does_not_block_other_handlers(self) -> None:
        received: list[str] = []

        class RaisingHandler(InstrumentationHandler):
            async def on_llm(self, span: LLMSpan) -> None:
                raise ValueError("intentional crash")

        class GoodHandler(InstrumentationHandler):
            async def on_llm(self, span: LLMSpan) -> None:
                received.append("ok")

        registry = _HandlerRegistry()
        registry.add(RaisingHandler())
        registry.add(GoodHandler())

        asyncio.run(registry.on_llm(_make_llm_span()))

        assert received == ["ok"]

    def test_multiple_crashes_all_good_handlers_still_called(self) -> None:
        """Every non-crashing handler must be called even when several others raise."""
        received: list[str] = []

        class CrashA(InstrumentationHandler):
            async def on_observe(self, span: ObserveSpan) -> None:
                raise RuntimeError("crash A")

        class GoodB(InstrumentationHandler):
            async def on_observe(self, span: ObserveSpan) -> None:
                received.append("B")

        class CrashC(InstrumentationHandler):
            async def on_observe(self, span: ObserveSpan) -> None:
                raise RuntimeError("crash C")

        class GoodD(InstrumentationHandler):
            async def on_observe(self, span: ObserveSpan) -> None:
                received.append("D")

        registry = _HandlerRegistry()
        for h in [CrashA(), GoodB(), CrashC(), GoodD()]:
            registry.add(h)

        asyncio.run(registry.on_observe(_make_observe_span()))

        assert sorted(received) == ["B", "D"]
