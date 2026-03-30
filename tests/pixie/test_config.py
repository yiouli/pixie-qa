"""Tests for pixie.config — PixieConfig and get_config()."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pixie.config import PixieConfig, RateLimitConfig, get_config


class TestGetConfigDefaults:
    """get_config() returns sensible defaults when no env vars are set."""

    @pytest.fixture(autouse=True)
    def _clear_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PIXIE_ROOT", raising=False)
        monkeypatch.delenv("PIXIE_DB_PATH", raising=False)
        monkeypatch.delenv("PIXIE_DB_ENGINE", raising=False)
        monkeypatch.delenv("PIXIE_DATASET_DIR", raising=False)
        monkeypatch.delenv("PIXIE_RATE_LIMIT_ENABLED", raising=False)
        monkeypatch.delenv("PIXIE_RATE_LIMIT_RPS", raising=False)
        monkeypatch.delenv("PIXIE_RATE_LIMIT_RPM", raising=False)
        monkeypatch.delenv("PIXIE_RATE_LIMIT_TPS", raising=False)
        monkeypatch.delenv("PIXIE_RATE_LIMIT_TPM", raising=False)

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

    def test_rate_limits_disabled_by_default(self) -> None:
        config = get_config()
        assert config.rate_limits is None


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

    def test_reads_rate_limit_defaults_when_enabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setenv("PIXIE_RATE_LIMIT_ENABLED", "true")
        monkeypatch.delenv("PIXIE_RATE_LIMIT_RPS", raising=False)
        monkeypatch.delenv("PIXIE_RATE_LIMIT_RPM", raising=False)
        monkeypatch.delenv("PIXIE_RATE_LIMIT_TPS", raising=False)
        monkeypatch.delenv("PIXIE_RATE_LIMIT_TPM", raising=False)
        monkeypatch.chdir(tmp_path)

        config = get_config()

        assert config.rate_limits == RateLimitConfig()

    def test_reads_rate_limit_overrides(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("PIXIE_RATE_LIMIT_RPS", "10")
        monkeypatch.setenv("PIXIE_RATE_LIMIT_RPM", "100")
        monkeypatch.setenv("PIXIE_RATE_LIMIT_TPS", "5000")
        monkeypatch.setenv("PIXIE_RATE_LIMIT_TPM", "200000")

        config = get_config()

        assert config.rate_limits == RateLimitConfig(
            rps=10.0,
            rpm=100.0,
            tps=5000.0,
            tpm=200000.0,
        )

    def test_loads_rate_limits_from_dotenv(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("PIXIE_RATE_LIMIT_ENABLED", raising=False)
        monkeypatch.delenv("PIXIE_RATE_LIMIT_RPS", raising=False)
        monkeypatch.delenv("PIXIE_RATE_LIMIT_RPM", raising=False)
        monkeypatch.delenv("PIXIE_RATE_LIMIT_TPS", raising=False)
        monkeypatch.delenv("PIXIE_RATE_LIMIT_TPM", raising=False)
        dotenv_path = tmp_path / ".env"
        dotenv_path.write_text(
            "\n".join(
                [
                    "PIXIE_RATE_LIMIT_ENABLED=true",
                    "PIXIE_RATE_LIMIT_RPS=12",
                    "PIXIE_RATE_LIMIT_RPM=240",
                ]
            ),
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)

        config = get_config()

        assert config.rate_limits == RateLimitConfig(
            rps=12.0,
            rpm=240.0,
            tps=10_000.0,
            tpm=500_000.0,
        )


class TestPixieConfigFrozen:
    """PixieConfig is an immutable frozen dataclass."""

    def test_cannot_mutate(self) -> None:
        config = PixieConfig()
        with pytest.raises(AttributeError):
            config.db_path = "mutated"  # type: ignore[misc]
