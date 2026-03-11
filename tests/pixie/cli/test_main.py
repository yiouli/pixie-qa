"""Tests for pixie.cli.main — top-level CLI entry point."""

from __future__ import annotations

import asyncio
import pathlib
from datetime import datetime, timezone

import pytest
from piccolo.engine.sqlite import SQLiteEngine

from pixie.cli.main import main
from pixie.dataset.store import DatasetStore
from pixie.instrumentation.spans import ObserveSpan
from pixie.storage.store import ObservationStore


def _seed_store(db_path: pathlib.Path) -> None:
    """Synchronously create tables and insert a root span into a temp DB."""

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
        await store.save(root)

    asyncio.run(_setup())


@pytest.fixture
def seeded_db(tmp_path: pathlib.Path) -> pathlib.Path:
    """Return the path to a temp SQLite DB seeded with one root span."""
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
    """Tests for `pixie dataset create` via the CLI entry point."""

    def test_creates_dataset(
        self,
        seeded_db: pathlib.Path,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ds_dir = tmp_path / "datasets"
        monkeypatch.setenv("PIXIE_DB_PATH", str(seeded_db))
        monkeypatch.setenv("PIXIE_DATASET_DIR", str(ds_dir))

        result = main([
            "dataset", "create", "my-dataset",
            "--trace-id", "bbbb0000000000000000000000000001",
        ])
        assert result == 0
        ds = DatasetStore(dataset_dir=ds_dir).get("my-dataset")
        assert len(ds.items) == 1

    def test_error_returns_1(
        self,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Create an empty DB (with tables but no data)
        db_path = tmp_path / "empty.db"

        async def _create_empty() -> None:
            engine = SQLiteEngine(path=str(db_path))
            s = ObservationStore(engine=engine)
            await s.create_tables()

        asyncio.run(_create_empty())

        monkeypatch.setenv("PIXIE_DB_PATH", str(db_path))
        monkeypatch.setenv("PIXIE_DATASET_DIR", str(tmp_path / "ds"))

        result = main([
            "dataset", "create", "fail",
            "--trace-id", "nonexistent",
        ])
        assert result == 1


class TestMainDatasetAppend:
    """Tests for `pixie dataset append` via the CLI entry point."""

    def test_appends_to_dataset(
        self,
        seeded_db: pathlib.Path,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ds_dir = tmp_path / "datasets"
        monkeypatch.setenv("PIXIE_DB_PATH", str(seeded_db))
        monkeypatch.setenv("PIXIE_DATASET_DIR", str(ds_dir))

        # Create the dataset first
        DatasetStore(dataset_dir=ds_dir).create("target")

        result = main([
            "dataset", "append", "target",
            "--trace-id", "bbbb0000000000000000000000000001",
        ])
        assert result == 0
        ds = DatasetStore(dataset_dir=ds_dir).get("target")
        assert len(ds.items) == 1

    def test_missing_dataset_returns_1(
        self,
        seeded_db: pathlib.Path,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("PIXIE_DB_PATH", str(seeded_db))
        monkeypatch.setenv("PIXIE_DATASET_DIR", str(tmp_path / "ds"))

        result = main([
            "dataset", "append", "nope",
            "--trace-id", "bbbb0000000000000000000000000001",
        ])
        assert result == 1
