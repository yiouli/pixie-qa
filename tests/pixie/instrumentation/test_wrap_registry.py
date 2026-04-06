"""Tests for pixie.instrumentation.wrap_registry."""

from __future__ import annotations

from pixie.instrumentation.wrap_registry import (
    clear_capture_registry,
    clear_input_registry,
    get_capture_registry,
    get_input_registry,
    init_capture_registry,
    set_input_registry,
)


class TestInputRegistry:
    def test_default_is_none(self) -> None:
        assert get_input_registry() is None

    def test_set_and_get(self) -> None:
        registry = {"key": "value"}
        set_input_registry(registry)
        assert get_input_registry() == {"key": "value"}

    def test_clear_returns_none(self) -> None:
        set_input_registry({"key": "value"})
        clear_input_registry()
        assert get_input_registry() is None


class TestCaptureRegistry:
    def test_default_is_none(self) -> None:
        assert get_capture_registry() is None

    def test_init_returns_empty_dict(self) -> None:
        reg = init_capture_registry()
        assert reg == {}
        assert get_capture_registry() is reg

    def test_mutations_are_visible(self) -> None:
        reg = init_capture_registry()
        reg["answer"] = 42
        assert get_capture_registry() == {"answer": 42}

    def test_clear_returns_none(self) -> None:
        init_capture_registry()
        clear_capture_registry()
        assert get_capture_registry() is None
