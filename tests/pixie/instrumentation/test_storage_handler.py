"""Tests for pixie.instrumentation.handlers — StorageHandler and enable_storage."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from pixie.instrumentation.handlers import StorageHandler
from pixie.instrumentation.spans import LLMSpan, ObserveSpan


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


class TestStorageHandlerOnObserve:
    """StorageHandler.on_observe() delegates to store.save()."""

    @pytest.mark.asyncio
    async def test_awaits_store_save_with_observe_span(self) -> None:
        store = MagicMock()
        store.save = AsyncMock()
        handler = StorageHandler(store)
        span = _make_observe_span()

        await handler.on_observe(span)

        store.save.assert_awaited_once_with(span)

    @pytest.mark.asyncio
    async def test_does_not_raise_when_store_save_raises(self) -> None:
        store = MagicMock()
        store.save = AsyncMock(side_effect=RuntimeError("db error"))
        handler = StorageHandler(store)
        span = _make_observe_span()

        # Should not raise
        await handler.on_observe(span)


class TestStorageHandlerOnLlm:
    """StorageHandler.on_llm() delegates to store.save()."""

    @pytest.mark.asyncio
    async def test_awaits_store_save_with_llm_span(self) -> None:
        store = MagicMock()
        store.save = AsyncMock()
        handler = StorageHandler(store)
        span = _make_llm_span()

        await handler.on_llm(span)

        store.save.assert_awaited_once_with(span)

    @pytest.mark.asyncio
    async def test_does_not_raise_when_store_save_raises(self) -> None:
        store = MagicMock()
        store.save = AsyncMock(side_effect=RuntimeError("db error"))
        handler = StorageHandler(store)
        span = _make_llm_span()

        # Should not raise
        await handler.on_llm(span)
