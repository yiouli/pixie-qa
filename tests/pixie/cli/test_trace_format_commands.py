"""Tests for pixie trace and format commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pixie.cli.format_command import format_trace_to_entry
from pixie.instrumentation.models import INPUT_DATA_KEY
from pixie.instrumentation.wrap import TraceLogProcessor, WrapNameCollisionError


class TestTraceLogProcessorWriteLine:
    """Tests for TraceLogProcessor.write_line (used for kwargs, LLM spans)."""

    def test_writes_kwargs_record(self, tmp_path: Path) -> None:
        output = tmp_path / "trace.jsonl"
        processor = TraceLogProcessor(str(output))
        processor.write_line(
            {"type": "kwargs", "value": {"question": "hello", "count": 42}}
        )

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
        assert entry["input_data"] == {"msg": "hi"}
        assert entry["evaluators"] == ["Factuality"]

        # eval_input should contain only 'input' purpose wraps (input_data
        # is injected by the runner at evaluation time, not in the dataset)
        assert len(entry["eval_input"]) == 1
        assert entry["eval_input"][0]["name"] == "user_input"
        assert entry["eval_input"][0]["value"] == "hello"

        # expectation should contain output wraps
        assert entry["expectation"] is not None
        assert len(entry["expectation"]) == 2

        assert entry["description"] == "transformed from trace.jsonl"

    def test_kwargs_only_produces_valid_entry(self, tmp_path: Path) -> None:
        """When no purpose=input wraps exist, kwargs alone produce a valid entry."""
        trace_file = tmp_path / "trace.jsonl"
        lines = [
            json.dumps({"type": "kwargs", "value": {"a": 1}}),
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
        assert entry["input_data"] == {"a": 1}
        # eval_input is empty when no purpose=input wraps exist
        assert len(entry["eval_input"]) == 0
        # expectation has output wraps
        assert entry["expectation"] is not None

    def test_empty_kwargs_produces_valid_entry(self, tmp_path: Path) -> None:
        """Even with empty kwargs and no wraps, entry is valid (kwargs value is {})."""
        trace_file = tmp_path / "trace.jsonl"
        trace_file.write_text(json.dumps({"type": "kwargs", "value": {}}) + "\n")

        output_file = tmp_path / "entry.json"
        format_trace_to_entry(trace_file, output_file)

        entry = json.loads(output_file.read_text())
        # eval_input is empty when there are no purpose=input wraps
        assert len(entry["eval_input"]) == 0

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
        expectation = entry["expectation"]
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
    """Tests for load_input_kwargs."""

    def test_loads_valid_json(self, tmp_path: Path) -> None:
        from pixie.harness.runner import load_input_kwargs

        f = tmp_path / "input.json"
        f.write_text('{"key": "value"}')
        result = load_input_kwargs(f)
        assert result == {"key": "value"}

    def test_file_not_found(self, tmp_path: Path) -> None:
        from pixie.harness.runner import load_input_kwargs

        with pytest.raises(FileNotFoundError):
            load_input_kwargs(tmp_path / "missing.json")

    def test_non_dict_raises(self, tmp_path: Path) -> None:
        from pixie.harness.runner import load_input_kwargs

        f = tmp_path / "input.json"
        f.write_text("[1, 2, 3]")
        with pytest.raises(ValueError, match="JSON object"):
            load_input_kwargs(f)


class TestTraceLogProcessorNameValidation:
    """Tests for wrap name collision detection in TraceLogProcessor."""

    def _make_log_record(self, body: dict[str, object]) -> MagicMock:
        """Create a mock ReadWriteLogRecord with the given body."""
        mock = MagicMock()
        mock.log_record.body = body
        return mock

    def test_reserved_key_collision_raises(self, tmp_path: Path) -> None:
        """Using the reserved INPUT_DATA_KEY as a wrap name raises."""
        processor = TraceLogProcessor(str(tmp_path / "trace.jsonl"))
        record = self._make_log_record(
            {"type": "wrap", "name": INPUT_DATA_KEY, "purpose": "input", "data": "x"}
        )
        with pytest.raises(WrapNameCollisionError, match="reserved key"):
            processor.on_emit(record)

    def test_duplicate_name_raises(self, tmp_path: Path) -> None:
        """Using the same wrap name twice raises."""
        processor = TraceLogProcessor(str(tmp_path / "trace.jsonl"))
        record1 = self._make_log_record(
            {"type": "wrap", "name": "my_data", "purpose": "input", "data": "a"}
        )
        record2 = self._make_log_record(
            {"type": "wrap", "name": "my_data", "purpose": "output", "data": "b"}
        )
        processor.on_emit(record1)
        with pytest.raises(WrapNameCollisionError, match="already used"):
            processor.on_emit(record2)

    def test_distinct_names_accepted(self, tmp_path: Path) -> None:
        """Different wrap names are accepted without error."""
        processor = TraceLogProcessor(str(tmp_path / "trace.jsonl"))
        for name in ("alpha", "beta", "gamma"):
            record = self._make_log_record(
                {"type": "wrap", "name": name, "purpose": "input", "data": "x"}
            )
            processor.on_emit(record)
        # All three lines should be written
        lines = (tmp_path / "trace.jsonl").read_text().strip().split("\n")
        assert len(lines) == 3

    def test_non_wrap_records_not_validated(self, tmp_path: Path) -> None:
        """Non-wrap records (kwargs, llm_span) skip name validation."""
        processor = TraceLogProcessor(str(tmp_path / "trace.jsonl"))
        for record_type in ("kwargs", "llm_span"):
            record = self._make_log_record(
                {"type": record_type, "name": INPUT_DATA_KEY}
            )
            processor.on_emit(record)  # should not raise
