"""Tests for pixie.cli.dataset_command — dataset create, list, and save."""

from __future__ import annotations

import pathlib
from datetime import datetime, timezone
from typing import Any

import pytest
import pytest_asyncio
from piccolo.engine.sqlite import SQLiteEngine

from pixie.cli.dataset_command import (
    dataset_create,
    dataset_list,
    dataset_save,
    format_dataset_table,
)
from pixie.dataset.store import DatasetStore
from pixie.instrumentation.spans import (
    AssistantMessage,
    LLMSpan,
    ObserveSpan,
    SystemMessage,
    TextContent,
    UserMessage,
)
from pixie.storage.evaluable import _Unset
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


@pytest.fixture
def named_observe_span() -> ObserveSpan:
    """A named child ObserveSpan for by-name selection testing."""
    return ObserveSpan(
        span_id="aaaa000000000003",
        trace_id="bbbb0000000000000000000000000001",
        parent_span_id="aaaa000000000001",
        started_at=datetime(2025, 1, 1, 12, 0, 0, 500000, tzinfo=timezone.utc),
        ended_at=datetime(2025, 1, 1, 12, 0, 0, 700000, tzinfo=timezone.utc),
        duration_ms=200.0,
        name="retriever",
        input="refund policy",
        output="Returns accepted within 30 days.",
        metadata={"source": "kb"},
        error=None,
    )


# ---------------------------------------------------------------------------
# dataset_create
# ---------------------------------------------------------------------------


class TestDatasetCreate:
    """Tests for dataset_create()."""

    def test_creates_empty_dataset(self, ds_store: DatasetStore) -> None:
        result = dataset_create(name="my-set", dataset_store=ds_store)
        assert result.name == "my-set"
        assert len(result.items) == 0

    def test_persists_to_disk(self, ds_store: DatasetStore) -> None:
        dataset_create(name="persisted", dataset_store=ds_store)
        reloaded = ds_store.get("persisted")
        assert reloaded.name == "persisted"
        assert len(reloaded.items) == 0

    def test_raises_on_duplicate(self, ds_store: DatasetStore) -> None:
        dataset_create(name="dup", dataset_store=ds_store)
        with pytest.raises(FileExistsError):
            dataset_create(name="dup", dataset_store=ds_store)


# ---------------------------------------------------------------------------
# dataset_list
# ---------------------------------------------------------------------------


class TestDatasetList:
    """Tests for dataset_list()."""

    def test_empty_when_no_datasets(self, ds_store: DatasetStore) -> None:
        rows = dataset_list(dataset_store=ds_store)
        assert rows == []

    def test_returns_metadata(self, ds_store: DatasetStore) -> None:
        ds_store.create("alpha")
        rows = dataset_list(dataset_store=ds_store)
        assert len(rows) == 1
        assert rows[0]["name"] == "alpha"
        assert rows[0]["row_count"] == 0
        assert "created_at" in rows[0]
        assert "updated_at" in rows[0]

    def test_row_count_reflects_items(self, ds_store: DatasetStore) -> None:
        from pixie.storage.evaluable import Evaluable

        ds_store.create("with-items", items=[
            Evaluable(eval_input="q1"),
            Evaluable(eval_input="q2"),
        ])
        rows = dataset_list(dataset_store=ds_store)
        assert rows[0]["row_count"] == 2

    def test_multiple_datasets_sorted(self, ds_store: DatasetStore) -> None:
        ds_store.create("beta")
        ds_store.create("alpha")
        rows = dataset_list(dataset_store=ds_store)
        names = [r["name"] for r in rows]
        assert names == ["alpha", "beta"]


# ---------------------------------------------------------------------------
# format_dataset_table
# ---------------------------------------------------------------------------


class TestFormatDatasetTable:
    """Tests for format_dataset_table()."""

    def test_empty_message(self) -> None:
        assert format_dataset_table([]) == "No datasets found."

    def test_table_format(self) -> None:
        rows: list[dict[str, Any]] = [
            {
                "name": "qa-set",
                "row_count": 5,
                "created_at": "2025-01-01 12:00:00",
                "updated_at": "2025-01-02 12:00:00",
            },
        ]
        output = format_dataset_table(rows)
        lines = output.strip().split("\n")
        assert len(lines) == 3  # header, separator, data
        assert "Name" in lines[0]
        assert "Rows" in lines[0]
        assert "Created" in lines[0]
        assert "Updated" in lines[0]
        assert "qa-set" in lines[2]
        assert "5" in lines[2]


# ---------------------------------------------------------------------------
# dataset_save
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDatasetSave:
    """Tests for dataset_save()."""

    async def test_saves_root_span_by_default(
        self,
        obs_store: ObservationStore,
        ds_store: DatasetStore,
        root_span: ObserveSpan,
        child_llm_span: LLMSpan,
    ) -> None:
        await obs_store.save_many([root_span, child_llm_span])
        ds_store.create("my-set")

        result = await dataset_save(
            name="my-set",
            observation_store=obs_store,
            dataset_store=ds_store,
        )
        assert len(result.items) == 1
        assert result.items[0].eval_input == {"query": "What is our refund policy?"}
        assert result.items[0].eval_output == "You can return items within 30 days."

    async def test_saves_last_llm_call(
        self,
        obs_store: ObservationStore,
        ds_store: DatasetStore,
        root_span: ObserveSpan,
        child_llm_span: LLMSpan,
    ) -> None:
        await obs_store.save_many([root_span, child_llm_span])
        ds_store.create("llm-set")

        result = await dataset_save(
            name="llm-set",
            observation_store=obs_store,
            dataset_store=ds_store,
            select="last_llm_call",
        )
        assert len(result.items) == 1
        # LLM span evaluable has output text
        assert result.items[0].eval_output == "You can return items within 30 days."

    async def test_saves_by_name(
        self,
        obs_store: ObservationStore,
        ds_store: DatasetStore,
        root_span: ObserveSpan,
        named_observe_span: ObserveSpan,
    ) -> None:
        await obs_store.save_many([root_span, named_observe_span])
        ds_store.create("named-set")

        result = await dataset_save(
            name="named-set",
            observation_store=obs_store,
            dataset_store=ds_store,
            select="by_name",
            span_name="retriever",
        )
        assert len(result.items) == 1
        assert result.items[0].eval_input == "refund policy"

    async def test_expected_output_applied(
        self,
        obs_store: ObservationStore,
        ds_store: DatasetStore,
        root_span: ObserveSpan,
    ) -> None:
        await obs_store.save(root_span)
        ds_store.create("expected-set")

        result = await dataset_save(
            name="expected-set",
            observation_store=obs_store,
            dataset_store=ds_store,
            expected_output="the expected answer",
        )
        assert result.items[0].expected_output == "the expected answer"

    async def test_expected_output_unset_by_default(
        self,
        obs_store: ObservationStore,
        ds_store: DatasetStore,
        root_span: ObserveSpan,
    ) -> None:
        await obs_store.save(root_span)
        ds_store.create("unset-set")

        result = await dataset_save(
            name="unset-set",
            observation_store=obs_store,
            dataset_store=ds_store,
        )
        assert isinstance(result.items[0].expected_output, _Unset)

    async def test_notes_attached(
        self,
        obs_store: ObservationStore,
        ds_store: DatasetStore,
        root_span: ObserveSpan,
    ) -> None:
        await obs_store.save(root_span)
        ds_store.create("notes-set")

        result = await dataset_save(
            name="notes-set",
            observation_store=obs_store,
            dataset_store=ds_store,
            notes="edge case for refund",
        )
        assert result.items[0].eval_metadata is not None
        assert result.items[0].eval_metadata["notes"] == "edge case for refund"

    async def test_raises_on_no_traces(
        self,
        obs_store: ObservationStore,
        ds_store: DatasetStore,
    ) -> None:
        ds_store.create("empty")
        with pytest.raises(ValueError, match="No traces found"):
            await dataset_save(
                name="empty",
                observation_store=obs_store,
                dataset_store=ds_store,
            )

    async def test_raises_on_missing_dataset(
        self,
        obs_store: ObservationStore,
        ds_store: DatasetStore,
        root_span: ObserveSpan,
    ) -> None:
        await obs_store.save(root_span)
        with pytest.raises(FileNotFoundError):
            await dataset_save(
                name="ghost",
                observation_store=obs_store,
                dataset_store=ds_store,
            )

    async def test_raises_no_llm_span(
        self,
        obs_store: ObservationStore,
        ds_store: DatasetStore,
        root_span: ObserveSpan,
    ) -> None:
        await obs_store.save(root_span)
        ds_store.create("no-llm")
        with pytest.raises(ValueError, match="No LLM span found"):
            await dataset_save(
                name="no-llm",
                observation_store=obs_store,
                dataset_store=ds_store,
                select="last_llm_call",
            )

    async def test_raises_by_name_without_span_name(
        self,
        obs_store: ObservationStore,
        ds_store: DatasetStore,
        root_span: ObserveSpan,
    ) -> None:
        await obs_store.save(root_span)
        ds_store.create("no-name")
        with pytest.raises(ValueError, match="--span-name is required"):
            await dataset_save(
                name="no-name",
                observation_store=obs_store,
                dataset_store=ds_store,
                select="by_name",
            )

    async def test_raises_by_name_not_found(
        self,
        obs_store: ObservationStore,
        ds_store: DatasetStore,
        root_span: ObserveSpan,
    ) -> None:
        await obs_store.save(root_span)
        ds_store.create("missing-name")
        with pytest.raises(ValueError, match="No span named"):
            await dataset_save(
                name="missing-name",
                observation_store=obs_store,
                dataset_store=ds_store,
                select="by_name",
                span_name="nonexistent",
            )
