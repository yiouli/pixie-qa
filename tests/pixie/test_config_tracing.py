"""Tests for pixie.config — new tracing fields."""

from __future__ import annotations

import pytest

from pixie.config import PixieConfig, get_config


class TestPixieConfigTracingFields:
    def test_defaults(self) -> None:
        config = PixieConfig()
        assert config.trace_output is None
        assert config.tracing_enabled is False

    def test_tracing_enabled_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PIXIE_TRACING", "1")
        config = get_config()
        assert config.tracing_enabled is True

    def test_tracing_disabled_when_env_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("PIXIE_TRACING", raising=False)
        config = get_config()
        assert config.tracing_enabled is False

    def test_tracing_disabled_when_env_zero(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_TRACING", "0")
        config = get_config()
        assert config.tracing_enabled is False

    def test_trace_output_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PIXIE_TRACE_OUTPUT", "traces/output.jsonl")
        config = get_config()
        assert config.trace_output == "traces/output.jsonl"

    def test_trace_output_default_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PIXIE_TRACE_OUTPUT", raising=False)
        config = get_config()
        assert config.trace_output is None
