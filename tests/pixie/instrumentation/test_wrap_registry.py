"""Tests for pixie.instrumentation.wrap_registry."""

from __future__ import annotations

from pixie.instrumentation.wrap import (
    clear_eval_input,
    clear_eval_output,
    get_eval_input,
    get_eval_output,
    init_eval_output,
    set_eval_input,
)


class TestEvalInput:
    def test_default_is_none(self) -> None:
        clear_eval_input()
        assert get_eval_input() is None

    def test_set_and_get(self) -> None:
        registry = {"key": "value"}
        set_eval_input(registry)
        assert get_eval_input() == {"key": "value"}
        clear_eval_input()

    def test_clear_returns_none(self) -> None:
        set_eval_input({"key": "value"})
        clear_eval_input()
        assert get_eval_input() is None


class TestEvalOutput:
    def test_default_is_none(self) -> None:
        clear_eval_output()
        assert get_eval_output() is None

    def test_init_returns_empty_list(self) -> None:
        out = init_eval_output()
        assert out == []
        assert get_eval_output() is out
        clear_eval_output()

    def test_mutations_are_visible(self) -> None:
        out = init_eval_output()
        out.append({"name": "x", "purpose": "output"})
        assert get_eval_output() == [{"name": "x", "purpose": "output"}]
        clear_eval_output()

    def test_clear_returns_none(self) -> None:
        init_eval_output()
        clear_eval_output()
        assert get_eval_output() is None
