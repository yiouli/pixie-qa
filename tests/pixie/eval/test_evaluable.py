"""Tests for pixie.eval.evaluable — collapse_named_data utility."""

from __future__ import annotations

from pixie.eval.evaluable import NamedData, collapse_named_data


def _nd(name: str, value: object) -> NamedData:
    return NamedData(name=name, value=value)


class TestCollapseNamedData:
    """Tests for collapse_named_data utility."""

    def test_empty_list_returns_none(self) -> None:
        assert collapse_named_data([]) is None

    def test_single_string_item_returns_value(self) -> None:
        result = collapse_named_data([_nd("answer", "42")])
        assert result == "42"

    def test_single_dict_item_returns_value(self) -> None:
        result = collapse_named_data([_nd("data", {"key": "val"})])
        assert result == {"key": "val"}

    def test_single_none_item_returns_none(self) -> None:
        result = collapse_named_data([_nd("empty", None)])
        assert result is None

    def test_multiple_items_returns_dict(self) -> None:
        result = collapse_named_data(
            [
                _nd("response", "Hello!"),
                _nd("function_called", "greet"),
                _nd("call_ended", True),
            ]
        )
        assert result == {
            "response": "Hello!",
            "function_called": "greet",
            "call_ended": True,
        }

    def test_multiple_items_preserves_order(self) -> None:
        result = collapse_named_data(
            [
                _nd("a", 1),
                _nd("b", 2),
                _nd("c", 3),
            ]
        )
        assert isinstance(result, dict)
        assert list(result.keys()) == ["a", "b", "c"]

    def test_multiple_items_with_nested_values(self) -> None:
        result = collapse_named_data(
            [
                _nd("transcript", [{"role": "user", "content": "hi"}]),
                _nd("score", 0.95),
            ]
        )
        assert result == {
            "transcript": [{"role": "user", "content": "hi"}],
            "score": 0.95,
        }
