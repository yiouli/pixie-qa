"""Tests for pixie.cli.test_command — eval test CLI entry point."""

from __future__ import annotations

from pathlib import Path

import pytest

import pixie.instrumentation as instrumentation
from pixie.cli import test_command
from pixie.evals.rate_limiter import configure_rate_limits, get_rate_limiter


class TestTestCommandRateLimitConfig:
    """Tests that pixie test applies central rate-limit config."""

    def teardown_method(self) -> None:
        configure_rate_limits(None)

    def test_loads_rate_limit_config_from_dotenv(
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
                    "PIXIE_RATE_LIMIT_RPS=7",
                    "PIXIE_RATE_LIMIT_RPM=70",
                ]
            ),
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(instrumentation, "init", lambda: None)
        monkeypatch.setattr(
            test_command, "discover_tests", lambda *_args, **_kwargs: []
        )
        monkeypatch.setattr(test_command, "run_tests", lambda _cases: [])
        monkeypatch.setattr(
            test_command, "format_results", lambda _results, verbose: "ok"
        )
        monkeypatch.setattr(
            test_command,
            "save_scorecard",
            lambda _report: str(tmp_path / "scorecard.html"),
        )

        result = test_command.main(["--no-open"])

        limiter = get_rate_limiter()
        assert result == 0
        assert limiter is not None
        assert limiter.config.rps == 7.0
        assert limiter.config.rpm == 70.0
