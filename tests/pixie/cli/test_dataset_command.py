"""Tests for pixie.cli.dataset_command — dataset create and append commands."""

from __future__ import annotations

import pathlib
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from piccolo.engine.sqlite import SQLiteEngine

from pixie.cli.dataset_command import dataset_append, dataset_create
from pixie.dataset.store import DatasetStore
from pixie.instrumentation.spans import (
    AssistantMessage,
    LLMSpan,
    ObserveSpan,
    SystemMessage,
    TextContent,
    UserMessage,
)
from pixie.storage.store import ObservationStore


@pytest_asyncio.fixture
async def obs_store(tmp_path: pathlib.Path) -> ObservationStore:
    """Provide a fresh ObservationStore backed by a temp SQLite database."""
    db_path = tmp_path / "test.db"
    engine = SQLiteEngine(path=str(db_path))
    store = ObservationStore(engine=engine)
    await store.create_tables()
    return store


@pytest.fixture
def ds_store(tmp_path: pathlib.Path) -> DatasetStore:
    """DatasetStore using a temporary directory."""
    return DatasetStore(dataset_dir=tmp_path / "datasets")


@pytest.fixture
def root_span() -> ObserveSpan:
    """A root ObserveSpan (no parent) for testing."""
    return ObserveSpan(
        span_id="aaaa000000000001",
        trace_id="bbbb0000000000000000000000000001",
        parent_span_id=None,
        started_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        ended_at=datetime(2025, 1, 1, 12, 0, 1, tzinfo=timezone.utc),
        duration_ms=1000.0,
        name="root_pipeline",
        input={"query": "What is our refund policy?"},
        output="You can return items within 30 days.",
        metadata={"env": "test"},
        error=None,
    )


@pytest.fixture
def child_llm_span() -> LLMSpan:
    """A child LLMSpan for testing."""
    return LLMSpan(
        span_id="aaaa000000000002",
        trace_id="bbbb0000000000000000000000000001",
        parent_span_id="aaaa000000000001",
        started_at=datetime(2025, 1, 1, 12, 0, 0, 100000, tzinfo=timezone.utc),
        ended_at=datetime(2025, 1, 1, 12, 0, 0, 450000, tzinfo=timezone.utc),
        duration_ms=350.0,
        operation="chat",
        provider="openai",
        request_model="gpt-4o",
        response_model="gpt-4o-2025-01-01",
        input_tokens=150,
        output_tokens=42,
        cache_read_tokens=30,
        cache_creation_tokens=0,
        request_temperature=0.7,
        request_max_tokens=1024,
        request_top_p=None,
        finish_reasons=("stop",),
        response_id="chatcmpl-123",
        output_type="text",
        error_type=None,
        input_messages=(
            SystemMessage(content="You are a helpful assistant."),
            UserMessage.from_text("What is our refund policy?"),
        ),
        output_messages=(
            AssistantMessage(
                content=(TextContent(text="You can return items within 30 days."),),
                tool_calls=(),
                finish_reason="stop",
            ),
        ),
        tool_definitions=(),
    )


# ---------------------------------------------------------------------------
# dataset_create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDatasetCreate:
    """Tests for dataset_create()."""

    async def test_creates_dataset_with_root_span(
        self,
        obs_store: ObservationStore,
        ds_store: DatasetStore,
        root_span: ObserveSpan,
        child_llm_span: LLMSpan,
    ) -> None:
        await obs_store.save_many([root_span, child_llm_span])

        result = await dataset_create(
            name="refund-qa",
            trace_id=root_span.trace_id,
            observation_store=obs_store,
            dataset_store=ds_store,
        )
        assert result.name == "refund-qa"
        assert len(result.items) == 1
        assert result.items[0].eval_input == {"query": "What is our refund policy?"}
        assert result.items[0].eval_output == "You can return items within 30 days."

    async def test_persists_dataset_to_disk(
        self,
        obs_store: ObservationStore,
        ds_store: DatasetStore,
        root_span: ObserveSpan,
    ) -> None:
        await obs_store.save(root_span)
        await dataset_create(
            name="persisted",
            trace_id=root_span.trace_id,
            observation_store=obs_store,
            dataset_store=ds_store,
        )
        reloaded = ds_store.get("persisted")
        assert len(reloaded.items) == 1

    async def test_raises_on_duplicate_name(
        self,
        obs_store: ObservationStore,
        ds_store: DatasetStore,
        root_span: ObserveSpan,
    ) -> None:
        await obs_store.save(root_span)
        await dataset_create(
            name="dup",
            trace_id=root_span.trace_id,
            observation_store=obs_store,
            dataset_store=ds_store,
        )
        with pytest.raises(FileExistsError):
            await dataset_create(
                name="dup",
                trace_id=root_span.trace_id,
                observation_store=obs_store,
                dataset_store=ds_store,
            )

    async def test_raises_on_missing_trace(
        self,
        obs_store: ObservationStore,
        ds_store: DatasetStore,
    ) -> None:
        with pytest.raises(ValueError, match="No root observation found"):
            await dataset_create(
                name="missing",
                trace_id="nonexistent",
                observation_store=obs_store,
                dataset_store=ds_store,
            )


# ---------------------------------------------------------------------------
# dataset_append
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDatasetAppend:
    """Tests for dataset_append()."""

    async def test_appends_root_span_to_existing_dataset(
        self,
        obs_store: ObservationStore,
        ds_store: DatasetStore,
        root_span: ObserveSpan,
    ) -> None:
        await obs_store.save(root_span)
        ds_store.create("my-set")

        result = await dataset_append(
            name="my-set",
            trace_id=root_span.trace_id,
            observation_store=obs_store,
            dataset_store=ds_store,
        )
        assert len(result.items) == 1
        assert result.items[0].eval_input == {"query": "What is our refund policy?"}

    async def test_appends_multiple_traces(
        self,
        obs_store: ObservationStore,
        ds_store: DatasetStore,
        root_span: ObserveSpan,
    ) -> None:
        await obs_store.save(root_span)

        second_root = ObserveSpan(
            span_id="cccc000000000001",
            trace_id="dddd0000000000000000000000000001",
            parent_span_id=None,
            started_at=datetime(2025, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
            ended_at=datetime(2025, 1, 2, 12, 0, 1, tzinfo=timezone.utc),
            duration_ms=1000.0,
            name="second_pipeline",
            input="hello",
            output="world",
            metadata={},
            error=None,
        )
        await obs_store.save(second_root)

        ds_store.create("multi")
        await dataset_append(
            name="multi",
            trace_id=root_span.trace_id,
            observation_store=obs_store,
            dataset_store=ds_store,
        )
        result = await dataset_append(
            name="multi",
            trace_id=second_root.trace_id,
            observation_store=obs_store,
            dataset_store=ds_store,
        )
        assert len(result.items) == 2

    async def test_raises_on_missing_dataset(
        self,
        obs_store: ObservationStore,
        ds_store: DatasetStore,
        root_span: ObserveSpan,
    ) -> None:
        await obs_store.save(root_span)
        with pytest.raises(FileNotFoundError):
            await dataset_append(
                name="ghost",
                trace_id=root_span.trace_id,
                observation_store=obs_store,
                dataset_store=ds_store,
            )

    async def test_raises_on_missing_trace(
        self,
        obs_store: ObservationStore,
        ds_store: DatasetStore,
    ) -> None:
        ds_store.create("empty")
        with pytest.raises(ValueError, match="No root observation found"):
            await dataset_append(
                name="empty",
                trace_id="nonexistent",
                observation_store=obs_store,
                dataset_store=ds_store,
            )
