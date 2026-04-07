"""Tests for pixie trace and format commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pixie.cli.format_command import format_trace_to_entry
from pixie.instrumentation.trace_writer import TraceFileWriter


class TestTraceFileWriterKwargs:
    """Tests for the new write_kwargs method."""

    def test_writes_kwargs_record(self, tmp_path: Path) -> None:
        output = tmp_path / "trace.jsonl"
        writer = TraceFileWriter(str(output))
        writer.write_kwargs({"question": "hello", "count": 42})

        lines = output.read_text().strip().split("\n")
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["type"] == "kwargs"
        assert record["value"] == {"question": "hello", "count": 42}


class TestFormatTraceToEntry:
    """Tests for the format command's core logic."""

    def test_basic_conversion(self, tmp_path: Path) -> None:
        """A trace with kwargs, input wraps, and output wraps produces a valid entry."""
        trace_file = tmp_path / "trace.jsonl"
        lines = [
            json.dumps({"type": "kwargs", "value": {"msg": "hi"}}),
            json.dumps(
                {
                    "type": "wrap",
                    "name": "user_input",
                    "purpose": "input",
                    "data": "hello",
                    "description": None,
                }
            ),
            json.dumps(
                {
                    "type": "wrap",
                    "name": "response",
                    "purpose": "output",
                    "data": "world",
                    "description": None,
                }
            ),
            json.dumps(
                {
                    "type": "wrap",
                    "name": "route",
                    "purpose": "state",
                    "data": "standard",
                    "description": None,
                }
            ),
        ]
        trace_file.write_text("\n".join(lines) + "\n")

        output_file = tmp_path / "entry.json"
        format_trace_to_entry(trace_file, output_file)

        entry = json.loads(output_file.read_text())
        assert entry["entry_kwargs"] == {"msg": "hi"}
        assert entry["evaluators"] == ["Factuality"]

        test_case = entry["test_case"]
        # eval_input should contain 'input' purpose wraps
        assert len(test_case["eval_input"]) == 1
        assert test_case["eval_input"][0]["name"] == "user_input"
        assert test_case["eval_input"][0]["value"] == "hello"

        # expectation should contain output wraps
        assert test_case["expectation"] is not None
        assert len(test_case["expectation"]) == 2

        assert test_case["description"] == "transformed from trace.jsonl"

    def test_no_input_falls_back_to_entry(self, tmp_path: Path) -> None:
        """When no purpose=input wraps exist, uses purpose=entry wraps."""
        trace_file = tmp_path / "trace.jsonl"
        lines = [
            json.dumps({"type": "kwargs", "value": {"a": 1}}),
            json.dumps(
                {
                    "type": "wrap",
                    "name": "msg",
                    "purpose": "entry",
                    "data": "hi",
                    "description": None,
                }
            ),
            json.dumps(
                {
                    "type": "wrap",
                    "name": "out",
                    "purpose": "output",
                    "data": "bye",
                    "description": None,
                }
            ),
        ]
        trace_file.write_text("\n".join(lines) + "\n")

        output_file = tmp_path / "entry.json"
        format_trace_to_entry(trace_file, output_file)

        entry = json.loads(output_file.read_text())
        assert entry["test_case"]["eval_input"][0]["name"] == "msg"

    def test_no_data_raises(self, tmp_path: Path) -> None:
        """Raises when trace has no usable input data."""
        trace_file = tmp_path / "trace.jsonl"
        trace_file.write_text(json.dumps({"type": "kwargs", "value": {}}) + "\n")

        output_file = tmp_path / "entry.json"
        with pytest.raises(ValueError, match="No input data"):
            format_trace_to_entry(trace_file, output_file)

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            format_trace_to_entry(
                tmp_path / "nonexistent.jsonl",
                tmp_path / "out.json",
            )

    def test_llm_span_included_in_expectation(self, tmp_path: Path) -> None:
        """LLM spans are included in expectation with metadata stripped."""
        trace_file = tmp_path / "trace.jsonl"
        lines = [
            json.dumps({"type": "kwargs", "value": {"q": "test"}}),
            json.dumps(
                {
                    "type": "wrap",
                    "name": "input_data",
                    "purpose": "input",
                    "data": "query",
                    "description": None,
                }
            ),
            json.dumps(
                {
                    "type": "llm_span",
                    "span_id": "abc123",
                    "trace_id": "def456",
                    "operation": "chat",
                    "provider": "openai",
                    "request_model": "gpt-4",
                    "input_messages": [{"role": "user", "content": "hi"}],
                    "output_messages": [{"role": "assistant", "content": "hello"}],
                    "started_at": "2025-01-01T00:00:00",
                    "ended_at": "2025-01-01T00:00:01",
                    "duration_ms": 1000.0,
                    "input_tokens": 10,
                    "output_tokens": 20,
                }
            ),
        ]
        trace_file.write_text("\n".join(lines) + "\n")

        output_file = tmp_path / "entry.json"
        format_trace_to_entry(trace_file, output_file)

        entry = json.loads(output_file.read_text())
        expectation = entry["test_case"]["expectation"]
        assert len(expectation) == 1
        # Should have LLM span with metadata stripped
        llm_item = expectation[0]
        assert llm_item["name"] == "llm_span_gpt-4"
        # Metadata-like fields should be stripped
        assert "span_id" not in llm_item["value"]
        assert "started_at" not in llm_item["value"]
        assert "input_tokens" not in llm_item["value"]
        # Semantic fields should be kept
        assert llm_item["value"]["operation"] == "chat"
        assert llm_item["value"]["provider"] == "openai"


class TestRunUtilsLoadInput:
    """Tests for run_utils.load_input_kwargs."""

    def test_loads_valid_json(self, tmp_path: Path) -> None:
        from pixie.evals.run_utils import load_input_kwargs

        f = tmp_path / "input.json"
        f.write_text('{"key": "value"}')
        result = load_input_kwargs(f)
        assert result == {"key": "value"}

    def test_file_not_found(self, tmp_path: Path) -> None:
        from pixie.evals.run_utils import load_input_kwargs

        with pytest.raises(FileNotFoundError):
            load_input_kwargs(tmp_path / "missing.json")

    def test_non_dict_raises(self, tmp_path: Path) -> None:
        from pixie.evals.run_utils import load_input_kwargs

        f = tmp_path / "input.json"
        f.write_text("[1, 2, 3]")
        with pytest.raises(ValueError, match="JSON object"):
            load_input_kwargs(f)
