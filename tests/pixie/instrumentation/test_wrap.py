"""Tests for pixie.instrumentation.wrap."""

from __future__ import annotations

import os
from typing import Any

import pytest

from pixie.instrumentation.wrap import WrapRegistryMissError, wrap
from pixie.instrumentation.wrap_registry import (
    clear_capture_registry,
    clear_input_registry,
    get_capture_registry,
    init_capture_registry,
    set_input_registry,
)
from pixie.instrumentation.wrap_serialization import serialize_wrap_data


@pytest.fixture(autouse=True)
def _clean_registries() -> Any:
    """Reset wrap registries before and after each test."""
    clear_input_registry()
    clear_capture_registry()
    yield
    clear_input_registry()
    clear_capture_registry()


@pytest.fixture(autouse=True)
def _no_tracing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure PIXIE_TRACING is unset for no-op / eval mode tests."""
    monkeypatch.delenv("PIXIE_TRACING", raising=False)


class TestNoOpMode:
    """wrap() returns data unchanged when no registry and tracing disabled."""

    def test_value_passthrough(self) -> None:
        result = wrap("hello", purpose="output", name="msg")
        assert result == "hello"

    def test_callable_passthrough(self) -> None:
        def fn() -> str:
            return "hi"

        result = wrap(fn, purpose="output", name="fn")
        assert result is fn

    def test_dict_passthrough(self) -> None:
        data = {"key": "value"}
        assert wrap(data, purpose="state", name="ctx") is data

    def test_none_passthrough(self) -> None:
        assert wrap(None, purpose="entry", name="x") is None


class TestEvalModeInput:
    """wrap(purpose='input') injects value from registry."""

    def test_injects_string_value(self) -> None:
        serialized = serialize_wrap_data("injected_value")
        set_input_registry({"my_dep": serialized})
        result = wrap("original", purpose="input", name="my_dep")
        assert result == "injected_value"

    def test_injects_dict_value(self) -> None:
        data = {"id": 1, "name": "Alice"}
        serialized = serialize_wrap_data(data)
        set_input_registry({"user": serialized})
        result: dict[str, object] = wrap({}, purpose="input", name="user")
        assert result == data

    def test_missing_key_raises(self) -> None:
        set_input_registry({"other_key": serialize_wrap_data("x")})
        with pytest.raises(WrapRegistryMissError) as exc_info:
            wrap("fallback", purpose="input", name="missing_key")
        assert "missing_key" in str(exc_info.value)

    def test_callable_returns_injected_value(self) -> None:
        serialized = serialize_wrap_data("db_record")
        set_input_registry({"record": serialized})

        def fetch_from_db() -> str:
            return "live_data"

        result_fn = wrap(fetch_from_db, purpose="input", name="record")
        assert callable(result_fn)
        assert result_fn() == "db_record"


class TestEvalModeOutput:
    """wrap(purpose='output') captures values into capture registry."""

    def test_captures_value(self) -> None:
        set_input_registry({})
        init_capture_registry()
        wrap("my_output", purpose="output", name="response")
        reg = get_capture_registry()
        assert reg is not None
        assert reg["response"] == "my_output"

    def test_captures_callable_result(self) -> None:
        set_input_registry({})
        init_capture_registry()

        def produce() -> str:
            return "produced"

        fn = wrap(produce, purpose="output", name="resp")
        assert callable(fn)
        fn()  # call triggers capture
        reg = get_capture_registry()
        assert reg is not None
        assert reg["resp"] == "produced"

    def test_returns_original_value_unchanged(self) -> None:
        set_input_registry({})
        init_capture_registry()
        data = {"x": 1}
        result = wrap(data, purpose="output", name="out")
        assert result is data


class TestEvalModeState:
    """wrap(purpose='state') captures intermediate state values."""

    def test_captures_state(self) -> None:
        set_input_registry({})
        init_capture_registry()
        wrap("route_a", purpose="state", name="route")
        reg = get_capture_registry()
        assert reg is not None
        assert reg["route"] == "route_a"


class TestEvalModeEntry:
    """wrap(purpose='entry') is a no-op even in eval mode."""

    def test_passthrough_in_eval_mode(self) -> None:
        set_input_registry({})
        init_capture_registry()
        data = "user_message"
        result = wrap(data, purpose="entry", name="input")
        assert result == data
        reg = get_capture_registry()
        assert reg is not None
        assert "input" not in reg


class TestTracingMode:
    """wrap() emits OTel events when PIXIE_TRACING=1."""

    def test_value_returned_unchanged(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_TRACING", "1")
        result = wrap("hello", purpose="output", name="msg")
        assert result == "hello"

    def test_callable_wraps_and_returns_result(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_TRACING", "1")

        def fn() -> str:
            return "result"

        wrapped = wrap(fn, purpose="output", name="fn")
        assert callable(wrapped)
        assert wrapped() == "result"

    def test_callable_returns_callable_not_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_TRACING", "1")

        def fn() -> int:
            return 99

        wrapped = wrap(fn, purpose="state", name="fn")
        # In tracing mode, wrap returns a callable that emits on call
        assert callable(wrapped)
