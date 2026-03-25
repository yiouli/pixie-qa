"""Tests for pixie.cli.trace_command — trace list, show, and last."""

from __future__ import annotations

import asyncio
import json
import pathlib
from datetime import datetime, timezone

import pytest
from piccolo.engine.sqlite import SQLiteEngine

from pixie.cli.main import main
from pixie.evals.llm_evaluator import _parse_score
from pixie.instrumentation.spans import (
    AssistantMessage,
    LLMSpan,
    ObserveSpan,
    SystemMessage,
    TextContent,
    UserMessage,
)
from pixie.storage.store import ObservationStore


def _seed_traces(db_path: pathlib.Path) -> None:
    """Create tables and insert two traces with multiple spans."""

    async def _setup() -> None:
        engine = SQLiteEngine(path=str(db_path))
        store = ObservationStore(engine=engine)
        await store.create_tables()

        # Trace 1: successful trace with root + LLM span
        root1 = ObserveSpan(
            span_id="aaaa000000000001",
            trace_id="bbbb0000000000000000000000000001",
            parent_span_id=None,
            started_at=datetime(2026, 3, 24, 20, 15, 0, tzinfo=timezone.utc),
            ended_at=datetime(2026, 3, 24, 20, 15, 1, tzinfo=timezone.utc),
            duration_ms=1000.0,
            name="voice_agent_turn",
            input={"user_message": "What are your hours?"},
            output="We're open 9-5 Monday through Friday.",
            metadata={},
            error=None,
        )
        llm1 = LLMSpan(
            span_id="aaaa000000000002",
            trace_id="bbbb0000000000000000000000000001",
            parent_span_id="aaaa000000000001",
            started_at=datetime(2026, 3, 24, 20, 15, 0, 100000, tzinfo=timezone.utc),
            ended_at=datetime(2026, 3, 24, 20, 15, 0, 850000, tzinfo=timezone.utc),
            duration_ms=750.0,
            operation="chat",
            provider="openai",
            request_model="gpt-4o-mini",
            response_model="gpt-4o-mini-2026-03-24",
            input_tokens=150,
            output_tokens=42,
            cache_read_tokens=0,
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
                UserMessage.from_text("What are your hours?"),
            ),
            output_messages=(
                AssistantMessage(
                    content=(
                        TextContent(text="We're open 9-5 Monday through Friday."),
                    ),
                    tool_calls=(),
                    finish_reason="stop",
                ),
            ),
            tool_definitions=(),
        )

        # Trace 2: trace with an error
        root2 = ObserveSpan(
            span_id="cccc000000000001",
            trace_id="dddd0000000000000000000000000002",
            parent_span_id=None,
            started_at=datetime(2026, 3, 24, 20, 10, 0, tzinfo=timezone.utc),
            ended_at=datetime(2026, 3, 24, 20, 10, 2, tzinfo=timezone.utc),
            duration_ms=2000.0,
            name="voice_agent_turn",
            input={"user_message": "Transfer me"},
            output=None,
            metadata={},
            error="TimeoutError: LLM call timed out",
        )

        await store.save_many([root1, llm1, root2])

    asyncio.run(_setup())


@pytest.fixture()
def trace_db(tmp_path: pathlib.Path) -> pathlib.Path:
    """Return path to a seeded SQLite DB."""
    db_path = tmp_path / "traces.db"
    _seed_traces(db_path)
    return db_path


class TestTraceListCLI:
    """Tests for ``pixie trace list``."""

    def test_list_shows_traces(
        self,
        trace_db: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("PIXIE_DB_PATH", str(trace_db))
        result = main(["trace", "list"])
        assert result == 0
        output = capsys.readouterr().out
        assert "voice_agent_turn" in output
        assert "TRACE_ID" in output

    def test_list_respects_limit(
        self,
        trace_db: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("PIXIE_DB_PATH", str(trace_db))
        result = main(["trace", "list", "--limit", "1"])
        assert result == 0
        output = capsys.readouterr().out
        # Should have header + 1 data row (most recent trace)
        lines = [line for line in output.strip().split("\n") if line.strip()]
        assert len(lines) == 2  # header + 1 trace

    def test_list_errors_filter(
        self,
        trace_db: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("PIXIE_DB_PATH", str(trace_db))
        result = main(["trace", "list", "--errors"])
        assert result == 0
        output = capsys.readouterr().out
        lines = [line for line in output.strip().split("\n") if line.strip()]
        # Header + 1 error trace
        assert len(lines) == 2
        assert "dddd" in output

    def test_list_empty_db(
        self,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        db_path = tmp_path / "empty.db"

        # Create empty DB
        async def _create() -> None:
            engine = SQLiteEngine(path=str(db_path))
            store = ObservationStore(engine=engine)
            await store.create_tables()

        asyncio.run(_create())
        monkeypatch.setenv("PIXIE_DB_PATH", str(db_path))
        result = main(["trace", "list"])
        assert result == 0
        assert "No traces found" in capsys.readouterr().out


class TestTraceShowCLI:
    """Tests for ``pixie trace show``."""

    def test_show_compact(
        self,
        trace_db: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("PIXIE_DB_PATH", str(trace_db))
        result = main(["trace", "show", "bbbb0000"])
        assert result == 0
        output = capsys.readouterr().out
        assert "voice_agent_turn" in output
        assert "gpt-4o-mini" in output

    def test_show_verbose(
        self,
        trace_db: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("PIXIE_DB_PATH", str(trace_db))
        result = main(["trace", "show", "bbbb0000", "-v"])
        assert result == 0
        output = capsys.readouterr().out
        assert "voice_agent_turn" in output
        assert "input:" in output
        assert "What are your hours?" in output

    def test_show_json(
        self,
        trace_db: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("PIXIE_DB_PATH", str(trace_db))
        result = main(["trace", "show", "bbbb0000", "--json"])
        assert result == 0
        output = capsys.readouterr().out
        data = json.loads(output)
        assert isinstance(data, list)
        assert len(data) == 2  # root + llm span

    def test_show_prefix_match(
        self,
        trace_db: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("PIXIE_DB_PATH", str(trace_db))
        # Short prefix should work
        result = main(["trace", "show", "bbbb0000"])
        assert result == 0

    def test_show_not_found(
        self,
        trace_db: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("PIXIE_DB_PATH", str(trace_db))
        result = main(["trace", "show", "zzzz0000"])
        assert result == 1
        assert "Error:" in capsys.readouterr().out


class TestTraceLastCLI:
    """Tests for ``pixie trace last``."""

    def test_last_shows_most_recent(
        self,
        trace_db: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("PIXIE_DB_PATH", str(trace_db))
        result = main(["trace", "last"])
        assert result == 0
        output = capsys.readouterr().out
        # Most recent is trace 1 (started at 20:15)
        assert "bbbb0000" in output
        assert "voice_agent_turn" in output

    def test_last_json(
        self,
        trace_db: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("PIXIE_DB_PATH", str(trace_db))
        result = main(["trace", "last", "--json"])
        assert result == 0
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, list)

    def test_last_empty_db(
        self,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        db_path = tmp_path / "empty.db"

        async def _create() -> None:
            engine = SQLiteEngine(path=str(db_path))
            store = ObservationStore(engine=engine)
            await store.create_tables()

        asyncio.run(_create())
        monkeypatch.setenv("PIXIE_DB_PATH", str(db_path))
        result = main(["trace", "last"])
        assert result == 0
        assert "No traces found" in capsys.readouterr().out


class TestParseScore:
    """Tests for _parse_score helper."""

    def test_standard_score_pattern(self) -> None:
        score, reasoning = _parse_score("Score: 0.8\nThe response was good.")
        assert score == 0.8

    def test_score_equals_pattern(self) -> None:
        score, _ = _parse_score("Score=1.0 Perfect.")
        assert score == 1.0

    def test_fraction_pattern(self) -> None:
        score, _ = _parse_score("I give this 0.7/1.0")
        assert score == 0.7

    def test_bare_float(self) -> None:
        score, _ = _parse_score("Good response.\n0.9\nNice work.")
        assert score == 0.9

    def test_no_score_returns_zero(self) -> None:
        score, reasoning = _parse_score("No score here.")
        assert score == 0.0
        assert "Failed to parse" in reasoning

    def test_clamps_to_range(self) -> None:
        score, _ = _parse_score("Score: 0.0")
        assert score == 0.0
        score, _ = _parse_score("Score: 1.0")
        assert score == 1.0
