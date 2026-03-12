"""Tests for pixie.config — PixieConfig and get_config()."""

from __future__ import annotations

import os

import pytest

from pixie.config import PixieConfig, get_config


class TestGetConfigDefaults:
    """get_config() returns sensible defaults when no env vars are set."""

    @pytest.fixture(autouse=True)
    def _clear_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PIXIE_ROOT", raising=False)
        monkeypatch.delenv("PIXIE_DB_PATH", raising=False)
        monkeypatch.delenv("PIXIE_DB_ENGINE", raising=False)
        monkeypatch.delenv("PIXIE_DATASET_DIR", raising=False)

    def test_default_root(self) -> None:
        config = get_config()
        assert config.root == "pixie_qa"

    def test_default_db_path(self) -> None:
        config = get_config()
        assert config.db_path == os.path.join("pixie_qa", "observations.db")

    def test_default_db_engine(self) -> None:
        config = get_config()
        assert config.db_engine == "sqlite"

    def test_default_dataset_dir(self) -> None:
        config = get_config()
        assert config.dataset_dir == os.path.join("pixie_qa", "datasets")


class TestGetConfigEnvOverrides:
    """get_config() reads PIXIE_* env vars when set."""

    def test_reads_pixie_root(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PIXIE_DB_PATH", raising=False)
        monkeypatch.delenv("PIXIE_DATASET_DIR", raising=False)
        monkeypatch.setenv("PIXIE_ROOT", "/tmp/my-pixie")
        config = get_config()
        assert config.root == "/tmp/my-pixie"
        assert config.db_path == "/tmp/my-pixie/observations.db"
        assert config.dataset_dir == "/tmp/my-pixie/datasets"

    def test_reads_pixie_db_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PIXIE_DB_PATH", "/tmp/custom.db")
        config = get_config()
        assert config.db_path == "/tmp/custom.db"

    def test_reads_pixie_db_engine(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PIXIE_DB_ENGINE", "postgres")
        config = get_config()
        assert config.db_engine == "postgres"

    def test_reads_pixie_dataset_dir(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PIXIE_DATASET_DIR", "/tmp/my-datasets")
        config = get_config()
        assert config.dataset_dir == "/tmp/my-datasets"


class TestPixieConfigFrozen:
    """PixieConfig is an immutable frozen dataclass."""

    def test_cannot_mutate(self) -> None:
        config = PixieConfig()
        with pytest.raises(AttributeError):
            config.db_path = "mutated"  # type: ignore[misc]
