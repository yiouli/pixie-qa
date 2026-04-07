"""Tests for pixie.instrumentation.wrap."""

from __future__ import annotations

from typing import Any

import pytest

from pixie.instrumentation.wrap import (
    WrapRegistryMissError,
    clear_eval_input,
    clear_eval_output,
    get_eval_output,
    init_eval_output,
    serialize_wrap_data,
    set_eval_input,
    wrap,
)


@pytest.fixture(autouse=True)
def _clean_registries() -> Any:
    """Reset wrap registries before and after each test."""
    clear_eval_input()
    clear_eval_output()
    yield
    clear_eval_input()
    clear_eval_output()


class TestDefaultMode:
    """wrap() emits via OTel logger and returns data or a callable wrapper."""

    def test_value_passthrough(self) -> None:
        result = wrap("hello", purpose="output", name="msg")
        assert result == "hello"

    def test_callable_returns_wrapper(self) -> None:
        def fn() -> str:
            return "hi"

        wrapped = wrap(fn, purpose="output", name="fn")
        assert callable(wrapped)
        assert wrapped() == "hi"

    def test_dict_passthrough(self) -> None:
        data = {"key": "value"}
        result = wrap(data, purpose="state", name="ctx")
        assert result is data

    def test_none_passthrough(self) -> None:
        assert wrap(None, purpose="input", name="x") is None


class TestEvalModeInput:
    """wrap(purpose='input') injects value from registry."""

    def test_injects_string_value(self) -> None:
        serialized = serialize_wrap_data("injected_value")
        set_eval_input({"my_dep": serialized})
        result = wrap("original", purpose="input", name="my_dep")
        assert result == "injected_value"

    def test_injects_dict_value(self) -> None:
        data = {"id": 1, "name": "Alice"}
        serialized = serialize_wrap_data(data)
        set_eval_input({"user": serialized})
        result: dict[str, object] = wrap({}, purpose="input", name="user")
        assert result == data

    def test_missing_key_raises(self) -> None:
        set_eval_input({"other_key": serialize_wrap_data("x")})
        with pytest.raises(WrapRegistryMissError) as exc_info:
            wrap("fallback", purpose="input", name="missing_key")
        assert "missing_key" in str(exc_info.value)

    def test_callable_returns_injected_value(self) -> None:
        serialized = serialize_wrap_data("db_record")
        set_eval_input({"record": serialized})

        def fetch_from_db() -> str:
            return "live_data"

        result_fn = wrap(fetch_from_db, purpose="input", name="record")
        assert callable(result_fn)
        assert result_fn() == "db_record"


class TestCaptureViaProcessor:
    """EvalCaptureLogProcessor captures output/state events into eval_output."""

    def test_captures_output_value(self) -> None:
        init_eval_output()
        wrap("my_output", purpose="output", name="response")
        out = get_eval_output()
        assert out is not None
        assert len(out) == 1
        assert out[0]["name"] == "response"
        assert out[0]["purpose"] == "output"

    def test_captures_callable_result(self) -> None:
        init_eval_output()

        def produce() -> str:
            return "produced"

        fn = wrap(produce, purpose="output", name="resp")
        assert callable(fn)
        fn()  # call triggers capture
        out = get_eval_output()
        assert out is not None
        assert len(out) == 1
        assert out[0]["name"] == "resp"

    def test_returns_original_value_unchanged(self) -> None:
        init_eval_output()
        data = {"x": 1}
        result = wrap(data, purpose="output", name="out")
        assert result is data

    def test_captures_state(self) -> None:
        init_eval_output()
        wrap("route_a", purpose="state", name="route")
        out = get_eval_output()
        assert out is not None
        assert len(out) == 1
        assert out[0]["name"] == "route"
        assert out[0]["purpose"] == "state"

    def test_no_capture_when_not_initialized(self) -> None:
        wrap("val", purpose="output", name="out")
        out = get_eval_output()
        assert out is None
