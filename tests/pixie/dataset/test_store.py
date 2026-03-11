"""Tests for pixie.dataset.store — DatasetStore JSON-file CRUD."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pixie.dataset.store import DatasetStore, _slugify
from pixie.storage.evaluable import Evaluable

# ---------------------------------------------------------------------------
# _slugify
# ---------------------------------------------------------------------------


class TestSlugify:
    """Tests for the _slugify helper."""

    def test_lowercase_and_dash(self) -> None:
        assert _slugify("My Test Cases") == "my-test-cases"

    def test_strips_leading_trailing_dashes(self) -> None:
        assert _slugify("--hello--") == "hello"

    def test_replaces_non_alphanumeric_runs(self) -> None:
        assert _slugify("foo@bar!baz") == "foo-bar-baz"

    def test_preserves_digits(self) -> None:
        assert _slugify("test-123") == "test-123"

    def test_raises_on_empty(self) -> None:
        with pytest.raises(ValueError, match="Cannot slugify"):
            _slugify("")

    def test_raises_on_non_alphanumeric_only(self) -> None:
        with pytest.raises(ValueError, match="Cannot slugify"):
            _slugify("@#$%")


# ---------------------------------------------------------------------------
# DatasetStore CRUD
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path: Path) -> DatasetStore:
    """DatasetStore using a temporary directory."""
    return DatasetStore(dataset_dir=tmp_path)


class TestCreate:
    """Tests for DatasetStore.create()."""

    def test_creates_json_file(self, store: DatasetStore, tmp_path: Path) -> None:
        store.create("my-set")
        assert (tmp_path / "my-set.json").exists()

    def test_returns_dataset(self, store: DatasetStore) -> None:
        ds = store.create("test", items=[Evaluable(eval_input="q")])
        assert ds.name == "test"
        assert len(ds.items) == 1

    def test_raises_on_duplicate(self, store: DatasetStore) -> None:
        store.create("dup")
        with pytest.raises(FileExistsError):
            store.create("dup")

    def test_file_content_is_valid_json(self, store: DatasetStore, tmp_path: Path) -> None:
        store.create(
            "qa",
            items=[Evaluable(eval_input="What is 2+2?", expected_output="4")],
        )
        raw = json.loads((tmp_path / "qa.json").read_text())
        assert raw["name"] == "qa"
        assert len(raw["items"]) == 1
        assert raw["items"][0]["eval_input"] == "What is 2+2?"
        assert raw["items"][0]["expected_output"] == "4"


class TestGet:
    """Tests for DatasetStore.get()."""

    def test_loads_dataset(self, store: DatasetStore) -> None:
        store.create("test", items=[Evaluable(eval_input="q")])
        ds = store.get("test")
        assert ds.name == "test"
        assert ds.items[0].eval_input == "q"

    def test_raises_on_missing(self, store: DatasetStore) -> None:
        with pytest.raises(FileNotFoundError):
            store.get("nonexistent")


class TestList:
    """Tests for DatasetStore.list()."""

    def test_returns_all_names(self, store: DatasetStore) -> None:
        store.create("alpha")
        store.create("beta")
        names = store.list()
        assert names == ["alpha", "beta"]

    def test_empty_when_dir_missing(self, tmp_path: Path) -> None:
        s = DatasetStore(dataset_dir=tmp_path / "nope")
        assert s.list() == []

    def test_skips_malformed_files(self, store: DatasetStore, tmp_path: Path) -> None:
        store.create("valid")
        (tmp_path / "bad.json").write_text("not json{{{", encoding="utf-8")
        names = store.list()
        assert names == ["valid"]


class TestDelete:
    """Tests for DatasetStore.delete()."""

    def test_removes_file(self, store: DatasetStore, tmp_path: Path) -> None:
        store.create("doomed")
        store.delete("doomed")
        assert not (tmp_path / "doomed.json").exists()

    def test_raises_on_missing(self, store: DatasetStore) -> None:
        with pytest.raises(FileNotFoundError):
            store.delete("ghost")


class TestAppend:
    """Tests for DatasetStore.append()."""

    def test_adds_items(self, store: DatasetStore) -> None:
        store.create("items")
        updated = store.append(
            "items",
            Evaluable(eval_input="q1"),
            Evaluable(eval_input="q2"),
        )
        assert len(updated.items) == 2
        # Verify persisted
        reloaded = store.get("items")
        assert len(reloaded.items) == 2

    def test_raises_on_missing(self, store: DatasetStore) -> None:
        with pytest.raises(FileNotFoundError):
            store.append("nope", Evaluable(eval_input="q"))


class TestRemove:
    """Tests for DatasetStore.remove()."""

    def test_removes_item_by_index(self, store: DatasetStore) -> None:
        store.create(
            "items",
            items=[
                Evaluable(eval_input="a"),
                Evaluable(eval_input="b"),
                Evaluable(eval_input="c"),
            ],
        )
        updated = store.remove("items", 1)
        assert len(updated.items) == 2
        assert updated.items[0].eval_input == "a"
        assert updated.items[1].eval_input == "c"

    def test_raises_on_out_of_range(self, store: DatasetStore) -> None:
        store.create("small", items=[Evaluable(eval_input="a")])
        with pytest.raises(IndexError):
            store.remove("small", 5)

    def test_raises_on_negative_index(self, store: DatasetStore) -> None:
        store.create("neg", items=[Evaluable(eval_input="a")])
        with pytest.raises(IndexError):
            store.remove("neg", -1)


class TestDatasetDirConfig:
    """Tests for directory configuration."""

    def test_creates_dir_on_first_write(self, tmp_path: Path) -> None:
        new_dir = tmp_path / "new" / "datasets"
        s = DatasetStore(dataset_dir=new_dir)
        s.create("test")
        assert new_dir.exists()

    def test_respects_env_var(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PIXIE_DATASET_DIR", str(tmp_path / "from-env"))
        s = DatasetStore()
        s.create("env-test")
        assert (tmp_path / "from-env" / "env-test.json").exists()
