"""Tests for pixie.instrumentation.wrap_log — WrappedData model and parsing."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pixie.instrumentation.wrap import (
    WrappedData,
    filter_by_purpose,
)


class TestWrappedDataModel:
    """Tests for the WrappedData Pydantic model."""

    def test_create_with_required_fields(self) -> None:
        wd = WrappedData(name="msg", purpose="input", data="hello")
        assert wd.name == "msg"
        assert wd.purpose == "input"
        assert wd.data == "hello"
        assert wd.type == "wrap"

    def test_frozen(self) -> None:
        wd = WrappedData(name="msg", purpose="input", data="hello")
        with pytest.raises(ValidationError):
            wd.name = "changed"


class TestFilterByPurpose:
    """Tests for purpose-based filtering."""

    def test_filters_entry_and_input(self) -> None:
        entries = [
            WrappedData(name="a", purpose="input", data=1),
            WrappedData(name="b", purpose="input", data=2),
            WrappedData(name="c", purpose="output", data=3),
        ]
        result = filter_by_purpose(entries, {"input"})
        assert len(result) == 2
        assert result[0].name == "a"
        assert result[1].name == "b"
