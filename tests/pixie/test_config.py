"""Tests for pixie.config — PixieConfig and get_config()."""

from __future__ import annotations

import pytest

from pixie.config import PixieConfig, get_config


class TestGetConfigDefaults:
    """get_config() returns sensible defaults when no env vars are set."""

    def test_default_db_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PIXIE_DB_PATH", raising=False)
        monkeypatch.delenv("PIXIE_DB_ENGINE", raising=False)
        config = get_config()
        assert config.db_path == "pixie_observations.db"

    def test_default_db_engine(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PIXIE_DB_PATH", raising=False)
        monkeypatch.delenv("PIXIE_DB_ENGINE", raising=False)
        config = get_config()
        assert config.db_engine == "sqlite"


class TestGetConfigEnvOverrides:
    """get_config() reads PIXIE_* env vars when set."""

    def test_reads_pixie_db_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PIXIE_DB_PATH", "/tmp/custom.db")
        config = get_config()
        assert config.db_path == "/tmp/custom.db"

    def test_reads_pixie_db_engine(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PIXIE_DB_ENGINE", "postgres")
        config = get_config()
        assert config.db_engine == "postgres"


class TestPixieConfigFrozen:
    """PixieConfig is an immutable frozen dataclass."""

    def test_cannot_mutate(self) -> None:
        config = PixieConfig()
        with pytest.raises(AttributeError):
            config.db_path = "mutated"  # type: ignore[misc]
