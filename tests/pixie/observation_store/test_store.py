"""Tests for pixie.storage.store — ObservationStore async operations."""

from __future__ import annotations

import pytest
import pytest_asyncio
from piccolo.engine.sqlite import SQLiteEngine

from pixie.instrumentation.spans import LLMSpan, ObserveSpan
from pixie.storage.store import ObservationStore


@pytest_asyncio.fixture
async def store(tmp_path: object) -> ObservationStore:  # type: ignore[override]
    """Provide a fresh ObservationStore backed by a temp SQLite database."""
    import pathlib

    db_path = pathlib.Path(str(tmp_path)) / "test.db"
    engine = SQLiteEngine(path=str(db_path))
    s = ObservationStore(engine=engine)
    await s.create_tables()
    return s


@pytest.mark.asyncio
class TestSaveAndGetTrace:
    """Tests for save + get_trace round-trips."""

    async def test_round_trip_observe_span(
        self,
        store: ObservationStore,
        sample_observe_span: ObserveSpan,
    ) -> None:
        await store.save(sample_observe_span)
        roots = await store.get_trace(sample_observe_span.trace_id)
        assert len(roots) == 1
        assert roots[0].span == sample_observe_span

    async def test_round_trip_llm_span(
        self,
        store: ObservationStore,
        sample_llm_span: LLMSpan,
    ) -> None:
        await store.save(sample_llm_span)
        roots = await store.get_trace(sample_llm_span.trace_id)
        assert len(roots) == 1
        assert roots[0].span == sample_llm_span

    async def test_save_many_builds_tree(
        self,
        store: ObservationStore,
        sample_observe_span: ObserveSpan,
        sample_llm_span: LLMSpan,
    ) -> None:
        await store.save_many([sample_observe_span, sample_llm_span])
        roots = await store.get_trace(sample_observe_span.trace_id)
        assert len(roots) == 1
        assert roots[0].span == sample_observe_span
        assert len(roots[0].children) == 1
        assert roots[0].children[0].span == sample_llm_span

    async def test_save_many_order_independent(
        self,
        store: ObservationStore,
        sample_observe_span: ObserveSpan,
        sample_llm_span: LLMSpan,
    ) -> None:
        # Save child before parent
        await store.save_many([sample_llm_span, sample_observe_span])
        roots = await store.get_trace(sample_observe_span.trace_id)
        assert len(roots) == 1
        assert roots[0].span == sample_observe_span
        assert len(roots[0].children) == 1


@pytest.mark.asyncio
class TestGetTraceFlat:
    """Tests for get_trace_flat."""

    async def test_ordered_by_started_at(
        self,
        store: ObservationStore,
        sample_observe_span: ObserveSpan,
        sample_llm_span: LLMSpan,
    ) -> None:
        await store.save_many([sample_llm_span, sample_observe_span])
        flat = await store.get_trace_flat(sample_observe_span.trace_id)
        assert len(flat) == 2
        assert flat[0] == sample_observe_span  # earlier started_at
        assert flat[1] == sample_llm_span


@pytest.mark.asyncio
class TestGetRoot:
    """Tests for get_root."""

    async def test_returns_root_observe_span(
        self,
        store: ObservationStore,
        sample_observe_span: ObserveSpan,
        sample_llm_span: LLMSpan,
    ) -> None:
        await store.save_many([sample_observe_span, sample_llm_span])
        root = await store.get_root(sample_observe_span.trace_id)
        assert root == sample_observe_span

    async def test_raises_for_nonexistent_trace(
        self,
        store: ObservationStore,
    ) -> None:
        with pytest.raises(ValueError, match="No root observation found"):
            await store.get_root("nonexistent_trace_id")


@pytest.mark.asyncio
class TestGetLastLLM:
    """Tests for get_last_llm."""

    async def test_returns_latest_llm_span(
        self,
        store: ObservationStore,
        sample_observe_span: ObserveSpan,
        sample_llm_span: LLMSpan,
        sample_llm_span_with_tools: LLMSpan,
    ) -> None:
        await store.save_many(
            [
                sample_observe_span,
                sample_llm_span,
                sample_llm_span_with_tools,
            ]
        )
        last = await store.get_last_llm(sample_observe_span.trace_id)
        assert last is not None
        # sample_llm_span_with_tools has later ended_at
        assert last == sample_llm_span_with_tools

    async def test_returns_none_when_no_llm(
        self,
        store: ObservationStore,
        sample_observe_span: ObserveSpan,
    ) -> None:
        await store.save(sample_observe_span)
        result = await store.get_last_llm(sample_observe_span.trace_id)
        assert result is None


@pytest.mark.asyncio
class TestGetByName:
    """Tests for get_by_name."""

    async def test_filters_by_name_in_trace(
        self,
        store: ObservationStore,
        sample_observe_span: ObserveSpan,
        sample_llm_span: LLMSpan,
    ) -> None:
        await store.save_many([sample_observe_span, sample_llm_span])
        results = await store.get_by_name("gpt-4o", trace_id=sample_observe_span.trace_id)
        assert len(results) == 1
        assert results[0] == sample_llm_span

    async def test_without_trace_returns_across_traces(
        self,
        store: ObservationStore,
        sample_llm_span: LLMSpan,
        sample_llm_span_with_image: LLMSpan,
    ) -> None:
        await store.save_many([sample_llm_span, sample_llm_span_with_image])
        results = await store.get_by_name("gpt-4o")
        assert len(results) == 2


@pytest.mark.asyncio
class TestGetByType:
    """Tests for get_by_type."""

    async def test_returns_only_llm_spans(
        self,
        store: ObservationStore,
        sample_observe_span: ObserveSpan,
        sample_llm_span: LLMSpan,
    ) -> None:
        await store.save_many([sample_observe_span, sample_llm_span])
        results = await store.get_by_type("llm", trace_id=sample_observe_span.trace_id)
        assert len(results) == 1
        assert isinstance(results[0], LLMSpan)


@pytest.mark.asyncio
class TestGetErrors:
    """Tests for get_errors."""

    async def test_returns_spans_with_errors(
        self,
        store: ObservationStore,
        sample_observe_span: ObserveSpan,
        sample_llm_span_empty_output: LLMSpan,
    ) -> None:
        await store.save_many(
            [
                sample_observe_span,
                sample_llm_span_empty_output,
            ]
        )
        errors = await store.get_errors()
        assert len(errors) == 1
        assert isinstance(errors[0], LLMSpan)

    async def test_scoped_to_trace(
        self,
        store: ObservationStore,
        sample_observe_span: ObserveSpan,
        sample_llm_span_empty_output: LLMSpan,
    ) -> None:
        await store.save_many(
            [
                sample_observe_span,
                sample_llm_span_empty_output,
            ]
        )
        # No errors in the observe span's trace
        errors = await store.get_errors(trace_id=sample_llm_span_empty_output.trace_id)
        assert len(errors) == 1


@pytest.mark.asyncio
class TestListTraces:
    """Tests for list_traces."""

    async def test_returns_summary_dicts(
        self,
        store: ObservationStore,
        sample_observe_span: ObserveSpan,
        sample_llm_span: LLMSpan,
    ) -> None:
        await store.save_many([sample_observe_span, sample_llm_span])
        traces = await store.list_traces()
        assert len(traces) == 1
        t = traces[0]
        assert t["trace_id"] == sample_observe_span.trace_id
        assert t["root_name"] == "root_pipeline"
        assert t["observation_count"] == 2
        assert t["has_error"] is False

    async def test_orders_most_recent_first(
        self,
        store: ObservationStore,
        sample_observe_span: ObserveSpan,
        sample_llm_span_with_image: LLMSpan,
    ) -> None:
        await store.save_many(
            [
                sample_observe_span,
                sample_llm_span_with_image,
            ]
        )
        traces = await store.list_traces()
        assert len(traces) == 2
        # Image span trace is more recent (13:00 vs 12:00)
        assert traces[0]["trace_id"] == sample_llm_span_with_image.trace_id

    async def test_respects_limit_and_offset(
        self,
        store: ObservationStore,
        sample_observe_span: ObserveSpan,
        sample_llm_span_with_image: LLMSpan,
    ) -> None:
        await store.save_many(
            [
                sample_observe_span,
                sample_llm_span_with_image,
            ]
        )
        traces = await store.list_traces(limit=1, offset=0)
        assert len(traces) == 1
        traces2 = await store.list_traces(limit=1, offset=1)
        assert len(traces2) == 1
        assert traces[0]["trace_id"] != traces2[0]["trace_id"]

    async def test_has_error_true(
        self,
        store: ObservationStore,
        sample_llm_span_empty_output: LLMSpan,
    ) -> None:
        await store.save(sample_llm_span_empty_output)
        traces = await store.list_traces()
        assert len(traces) == 1
        assert traces[0]["has_error"] is True
