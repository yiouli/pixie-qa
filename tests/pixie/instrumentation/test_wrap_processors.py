"""Tests for pixie.instrumentation.wrap_processors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pixie.instrumentation.wrap import (
    TraceLogProcessor,
    clear_eval_input,
    clear_eval_output,
    get_eval_output,
    init_eval_output,
    logger_provider,
    wrap,
)


@pytest.fixture(autouse=True)
def _clean_registries() -> Any:
    """Reset wrap registries before and after each test."""
    clear_eval_input()
    clear_eval_output()
    yield
    clear_eval_input()
    clear_eval_output()


class TestTraceLogProcessor:
    """TraceLogProcessor writes wrap events to a JSONL trace file."""

    def test_writes_wrap_event(self, tmp_path: Path) -> None:
        trace_file = str(tmp_path / "trace.jsonl")
        processor = TraceLogProcessor(trace_file)
        logger_provider.add_log_record_processor(processor)

        wrap("hello", purpose="output", name="msg", description="test message")

        lines = Path(trace_file).read_text().strip().splitlines()
        assert len(lines) >= 1
        record = json.loads(lines[-1])
        assert record["type"] == "wrap"
        assert record["name"] == "msg"
        assert record["purpose"] == "output"
        assert record["description"] == "test message"

    def test_writes_callable_result_on_call(self, tmp_path: Path) -> None:
        trace_file = str(tmp_path / "trace.jsonl")
        processor = TraceLogProcessor(trace_file)
        logger_provider.add_log_record_processor(processor)

        def fn() -> str:
            return "result"

        wrapped = wrap(fn, purpose="output", name="fn")
        assert callable(wrapped)

        # No wrap event yet for callable (emitted on call)
        initial_lines = Path(trace_file).read_text().strip().splitlines()
        initial_count = len([ln for ln in initial_lines if ln])

        result = wrapped()
        assert result == "result"

        lines = Path(trace_file).read_text().strip().splitlines()
        assert len(lines) > initial_count
        record = json.loads(lines[-1])
        assert record["name"] == "fn"
        assert record["purpose"] == "output"

    def test_write_line(self, tmp_path: Path) -> None:
        trace_file = str(tmp_path / "trace.jsonl")
        processor = TraceLogProcessor(trace_file)
        processor.write_line({"type": "kwargs", "value": {"q": "test"}})

        lines = Path(trace_file).read_text().strip().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["type"] == "kwargs"
        assert record["value"] == {"q": "test"}


class TestEvalCaptureLogProcessor:
    """EvalCaptureLogProcessor appends output/state bodies to eval_output.

    The processor is registered once in conftest.py.
    """

    def test_captures_output(self) -> None:
        init_eval_output()
        wrap("my_output", purpose="output", name="resp")
        out = get_eval_output()
        assert out is not None
        assert len(out) == 1
        assert out[0]["name"] == "resp"
        assert out[0]["purpose"] == "output"

    def test_captures_state(self) -> None:
        init_eval_output()
        wrap("route_a", purpose="state", name="route")
        out = get_eval_output()
        assert out is not None
        assert len(out) == 1
        assert out[0]["name"] == "route"
        assert out[0]["purpose"] == "state"

    def test_ignores_input_purpose(self) -> None:
        init_eval_output()
        # Without eval_input set, input purpose goes to _emit_and_return
        wrap("data", purpose="input", name="dep")
        out = get_eval_output()
        assert out is not None
        assert len(out) == 0

    def test_noop_when_not_initialized(self) -> None:
        # No init_eval_output() — processor should not crash
        wrap("val", purpose="output", name="out")
        assert get_eval_output() is None
