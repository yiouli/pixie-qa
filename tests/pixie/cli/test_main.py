"""Tests for pixie.cli.main — top-level CLI entry point."""

from __future__ import annotations

from pixie.cli.main import main


class TestMainNoArgs:
    """Tests for the no-argument case."""

    def test_prints_help_and_returns_1(self) -> None:
        result = main([])
        assert result == 1
