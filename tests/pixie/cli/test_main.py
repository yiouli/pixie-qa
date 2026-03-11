"""Tests for pixie.cli.main — top-level CLI entry point."""

from __future__ import annotations

import asyncio
import pathlib
from datetime import datetime, timezone

import pytest
from piccolo.engine.sqlite import SQLiteEngine

from pixie.cli.main import main
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


def _seed_store(db_path: pathlib.Path) -> None:
    """Synchronously create tables and insert a root span + LLM span."""

    async def _setup() -> None:
        engine = SQLiteEngine(path=str(db_path))
        store = ObservationStore(engine=engine)
        await store.create_tables()
        root = ObserveSpan(
            span_id="aaaa000000000001",
            trace_id="bbbb0000000000000000000000000001",
            parent_span_id=None,
            started_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            ended_at=datetime(2025, 1, 1, 12, 0, 1, tzinfo=timezone.utc),
            duration_ms=1000.0,
            name="root",
            input="hello",
            output="world",
            metadata={},
            error=None,
        )
        llm = LLMSpan(
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
                UserMessage.from_text("hello"),
            ),
            output_messages=(
                AssistantMessage(
                    content=(TextContent(text="world"),),
                    tool_calls=(),
                    finish_reason="stop",
                ),
            ),
            tool_definitions=(),
        )
        await store.save_many([root, llm])

    asyncio.run(_setup())


@pytest.fixture
def seeded_db(tmp_path: pathlib.Path) -> pathlib.Path:
    """Return the path to a temp SQLite DB seeded with one trace."""
    db_path = tmp_path / "test.db"
    _seed_store(db_path)
    return db_path


class TestMainNoArgs:
    """Tests for the no-argument case."""

    def test_prints_help_and_returns_1(self) -> None:
        result = main([])
        assert result == 1


class TestMainDatasetNoAction:
    """Tests for `pixie dataset` with no subaction."""

    def test_returns_1(self) -> None:
        with pytest.raises(SystemExit):
            main(["dataset"])


class TestMainDatasetCreate:
    """Tests for `pixie dataset create`."""

    def test_creates_empty_dataset(
        self,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ds_dir = tmp_path / "datasets"
        monkeypatch.setenv("PIXIE_DATASET_DIR", str(ds_dir))

        result = main(["dataset", "create", "my-dataset"])
        assert result == 0
        ds = DatasetStore(dataset_dir=ds_dir).get("my-dataset")
        assert len(ds.items) == 0

    def test_duplicate_returns_1(
        self,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ds_dir = tmp_path / "datasets"
        monkeypatch.setenv("PIXIE_DATASET_DIR", str(ds_dir))

        main(["dataset", "create", "dup"])
        result = main(["dataset", "create", "dup"])
        assert result == 1


class TestMainDatasetList:
    """Tests for `pixie dataset list`."""

    def test_list_empty(
        self,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("PIXIE_DATASET_DIR", str(tmp_path / "datasets"))
        result = main(["dataset", "list"])
        assert result == 0
        assert "No datasets found" in capsys.readouterr().out

    def test_list_shows_datasets(
        self,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        ds_dir = tmp_path / "datasets"
        monkeypatch.setenv("PIXIE_DATASET_DIR", str(ds_dir))
        DatasetStore(dataset_dir=ds_dir).create("alpha")
        DatasetStore(dataset_dir=ds_dir).create("beta")

        result = main(["dataset", "list"])
        assert result == 0
        output = capsys.readouterr().out
        assert "alpha" in output
        assert "beta" in output


class TestMainDatasetSave:
    """Tests for `pixie dataset save`."""

    def test_saves_root_span(
        self,
        seeded_db: pathlib.Path,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ds_dir = tmp_path / "datasets"
        monkeypatch.setenv("PIXIE_DB_PATH", str(seeded_db))
        monkeypatch.setenv("PIXIE_DATASET_DIR", str(ds_dir))
        DatasetStore(dataset_dir=ds_dir).create("target")

        result = main(["dataset", "save", "target"])
        assert result == 0
        ds = DatasetStore(dataset_dir=ds_dir).get("target")
        assert len(ds.items) == 1

    def test_saves_last_llm_call(
        self,
        seeded_db: pathlib.Path,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ds_dir = tmp_path / "datasets"
        monkeypatch.setenv("PIXIE_DB_PATH", str(seeded_db))
        monkeypatch.setenv("PIXIE_DATASET_DIR", str(ds_dir))
        DatasetStore(dataset_dir=ds_dir).create("llm-target")

        result = main([
            "dataset", "save", "llm-target",
            "--select", "last_llm_call",
        ])
        assert result == 0
        ds = DatasetStore(dataset_dir=ds_dir).get("llm-target")
        assert len(ds.items) == 1
        assert ds.items[0].eval_output == "world"

    def test_saves_with_notes(
        self,
        seeded_db: pathlib.Path,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ds_dir = tmp_path / "datasets"
        monkeypatch.setenv("PIXIE_DB_PATH", str(seeded_db))
        monkeypatch.setenv("PIXIE_DATASET_DIR", str(ds_dir))
        DatasetStore(dataset_dir=ds_dir).create("noted")

        result = main([
            "dataset", "save", "noted",
            "--notes", "edge case",
        ])
        assert result == 0
        ds = DatasetStore(dataset_dir=ds_dir).get("noted")
        assert ds.items[0].eval_metadata is not None
        assert ds.items[0].eval_metadata["notes"] == "edge case"

    def test_missing_dataset_returns_1(
        self,
        seeded_db: pathlib.Path,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("PIXIE_DB_PATH", str(seeded_db))
        monkeypatch.setenv("PIXIE_DATASET_DIR", str(tmp_path / "ds"))

        result = main(["dataset", "save", "nope"])
        assert result == 1

    def test_no_traces_returns_1(
        self,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        db_path = tmp_path / "empty.db"

        async def _create_empty() -> None:
            engine = SQLiteEngine(path=str(db_path))
            s = ObservationStore(engine=engine)
            await s.create_tables()

        asyncio.run(_create_empty())

        ds_dir = tmp_path / "datasets"
        monkeypatch.setenv("PIXIE_DB_PATH", str(db_path))
        monkeypatch.setenv("PIXIE_DATASET_DIR", str(ds_dir))
        DatasetStore(dataset_dir=ds_dir).create("empty")

        result = main(["dataset", "save", "empty"])
        assert result == 1
