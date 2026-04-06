"""Tests for pixie.instrumentation.wrap_serialization."""

from __future__ import annotations

from pixie.instrumentation.wrap_serialization import (
    deserialize_wrap_data,
    serialize_wrap_data,
)


class TestSerializeWrapData:
    def test_string_roundtrip(self) -> None:
        assert deserialize_wrap_data(serialize_wrap_data("hello")) == "hello"

    def test_int_roundtrip(self) -> None:
        assert deserialize_wrap_data(serialize_wrap_data(42)) == 42

    def test_dict_roundtrip(self) -> None:
        data = {"key": "value", "num": 3}
        assert deserialize_wrap_data(serialize_wrap_data(data)) == data

    def test_list_roundtrip(self) -> None:
        data = [1, 2, "three"]
        assert deserialize_wrap_data(serialize_wrap_data(data)) == data

    def test_none_roundtrip(self) -> None:
        assert deserialize_wrap_data(serialize_wrap_data(None)) is None

    def test_returns_string(self) -> None:
        result = serialize_wrap_data({"a": 1})
        assert isinstance(result, str)

    def test_output_is_valid_json(self) -> None:
        import json

        result = serialize_wrap_data({"x": [1, 2, 3]})
        parsed = json.loads(result)
        assert parsed["x"] == [1, 2, 3]
