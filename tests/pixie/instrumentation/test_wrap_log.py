"""Tests for pixie.instrumentation.wrap_log — WrappedData model and parsing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pixie.instrumentation.wrap import (
    WrapLogEntry,
    WrappedData,
    filter_by_purpose,
    load_wrap_log_entries,
    parse_wrapped_data_list,
)


class TestWrappedDataModel:
    """Tests for the WrappedData Pydantic model."""

    def test_create_with_required_fields(self) -> None:
        wd = WrappedData(name="msg", purpose="entry", data="hello")
        assert wd.name == "msg"
        assert wd.purpose == "entry"
        assert wd.data == "hello"
        assert wd.type == "wrap"

    def test_frozen(self) -> None:
        wd = WrappedData(name="msg", purpose="entry", data="hello")
        with pytest.raises(ValidationError):
            wd.name = "changed"

    def test_wrap_log_entry_is_alias(self) -> None:
        assert WrapLogEntry is WrappedData


class TestParseWrappedDataList:
    """Tests for parse_wrapped_data_list validation."""

    def test_valid_list(self) -> None:
        raw = [
            {"type": "wrap", "name": "msg", "purpose": "entry", "data": "hello"},
            {"type": "wrap", "name": "profile", "purpose": "input", "data": {"id": 1}},
        ]
        result = parse_wrapped_data_list(raw)
        assert len(result) == 2
        assert result[0].name == "msg"
        assert result[0].purpose == "entry"
        assert result[1].name == "profile"
        assert result[1].purpose == "input"

    def test_rejects_non_list(self) -> None:
        with pytest.raises(ValueError, match="list of WrappedData"):
            parse_wrapped_data_list({"key": "value"})

    def test_rejects_string(self) -> None:
        with pytest.raises(ValueError, match="list of WrappedData"):
            parse_wrapped_data_list("hello")

    def test_rejects_none(self) -> None:
        with pytest.raises(ValueError, match="list of WrappedData"):
            parse_wrapped_data_list(None)

    def test_rejects_item_without_purpose(self) -> None:
        with pytest.raises(ValueError, match="missing required 'purpose'"):
            parse_wrapped_data_list([{"name": "msg", "data": "hello"}])

    def test_rejects_item_without_name(self) -> None:
        with pytest.raises(ValueError, match="missing required 'purpose'"):
            parse_wrapped_data_list([{"purpose": "entry", "data": "hello"}])

    def test_rejects_non_dict_item(self) -> None:
        with pytest.raises(ValueError, match="expected a WrappedData object"):
            parse_wrapped_data_list(["not a dict"])


class TestLoadWrapLogEntries:
    """Tests for JSONL file loading."""

    def test_loads_wrap_entries(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "trace.jsonl"
        lines = [
            json.dumps({"type": "wrap", "name": "msg", "purpose": "entry", "data": "hi"}),
            json.dumps({"type": "llm_span", "span_id": "abc"}),
            json.dumps({"type": "wrap", "name": "out", "purpose": "output", "data": "bye"}),
        ]
        jsonl.write_text("\n".join(lines))
        entries = load_wrap_log_entries(jsonl)
        assert len(entries) == 2
        assert entries[0].name == "msg"
        assert entries[1].name == "out"

    def test_skips_malformed_lines(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "trace.jsonl"
        jsonl.write_text("not json\n")
        entries = load_wrap_log_entries(jsonl)
        assert entries == []


class TestFilterByPurpose:
    """Tests for purpose-based filtering."""

    def test_filters_entry_and_input(self) -> None:
        entries = [
            WrappedData(name="a", purpose="entry", data=1),
            WrappedData(name="b", purpose="input", data=2),
            WrappedData(name="c", purpose="output", data=3),
        ]
        result = filter_by_purpose(entries, {"entry", "input"})
        assert len(result) == 2
        assert result[0].name == "a"
        assert result[1].name == "b"
