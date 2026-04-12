"""Tests for pixie.eval.evaluable — collapse_named_data utility and model validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pixie.eval.evaluable import Evaluable, NamedData, TestCase, collapse_named_data


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


class TestTestCaseEvalInput:
    """Tests for TestCase.eval_input accepting empty lists."""

    def test_empty_eval_input_allowed(self) -> None:
        """TestCase (used by DatasetEntry) accepts empty eval_input."""
        tc = TestCase(eval_input=[], description="test")
        assert tc.eval_input == []

    def test_default_eval_input_is_empty(self) -> None:
        """TestCase defaults eval_input to empty list."""
        tc = TestCase(description="test")
        assert tc.eval_input == []

    def test_non_empty_eval_input_still_works(self) -> None:
        tc = TestCase(
            eval_input=[_nd("q", "hello")],
            description="test",
        )
        assert len(tc.eval_input) == 1


class TestEvaluableEvalInputValidation:
    """Tests for Evaluable requiring non-empty eval_input."""

    def test_evaluable_with_eval_input_succeeds(self) -> None:
        evaluable = Evaluable(
            eval_input=[_nd("input_data", {"q": "hi"})],
            eval_output=[_nd("output", "hello")],
            description="test",
        )
        assert len(evaluable.eval_input) == 1

    def test_evaluable_with_empty_eval_input_raises(self) -> None:
        """Evaluable rejects empty eval_input — runner must prepend input_data."""
        with pytest.raises(ValidationError, match="eval_input"):
            Evaluable(
                eval_input=[],
                eval_output=[_nd("output", "hello")],
                description="test",
            )

    def test_evaluable_with_multiple_eval_input_succeeds(self) -> None:
        """Evaluable accepts multiple eval_input items (input_data + wraps)."""
        evaluable = Evaluable(
            eval_input=[
                _nd("input_data", {"msg": "hi"}),
                _nd("profile", {"tier": "gold"}),
            ],
            eval_output=[_nd("response", "hello")],
            description="test",
        )
        assert len(evaluable.eval_input) == 2
