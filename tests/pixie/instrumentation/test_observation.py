"""Tests for the @observe decorator."""

from __future__ import annotations

import pytest

import pixie.instrumentation as px
from pixie.instrumentation.observation import observe

from .conftest import RecordingHandler


class TestObserveDecorator:
    """Tests for the @observe decorator."""

    def test_sync_function_captured(self, recording_handler: RecordingHandler) -> None:
        """@observe captures sync function input and output as an ObserveSpan."""
        px.init()
        px.add_handler(recording_handler)

        @observe()
        def greet(name: str) -> str:
            return f"Hello, {name}!"

        result = greet("Alice")
        px.flush()

        assert result == "Hello, Alice!"
        assert len(recording_handler.observe_spans) == 1
        obs = recording_handler.observe_spans[0]
        assert obs.name == "greet"
        assert "Alice" in obs.input
        assert "Hello, Alice!" in obs.output

    @pytest.mark.asyncio
    async def test_async_function_captured(
        self, recording_handler: RecordingHandler
    ) -> None:
        """@observe captures async function input and output."""
        px.init()
        px.add_handler(recording_handler)

        @observe()
        async def greet(name: str) -> str:
            return f"Hello, {name}!"

        result = await greet("Bob")
        px.flush()

        assert result == "Hello, Bob!"
        assert len(recording_handler.observe_spans) == 1
        obs = recording_handler.observe_spans[0]
        assert obs.name == "greet"

    def test_custom_name(self, recording_handler: RecordingHandler) -> None:
        """@observe(name=...) uses the custom name."""
        px.init()
        px.add_handler(recording_handler)

        @observe(name="custom_op")
        def work(x: int) -> int:
            return x * 2

        work(5)
        px.flush()

        obs = recording_handler.observe_spans[0]
        assert obs.name == "custom_op"

    def test_default_name_is_function_name(
        self, recording_handler: RecordingHandler
    ) -> None:
        """@observe() without name uses fn.__name__."""
        px.init()
        px.add_handler(recording_handler)

        @observe()
        def my_special_fn(x: int) -> int:
            return x

        my_special_fn(1)
        px.flush()

        obs = recording_handler.observe_spans[0]
        assert obs.name == "my_special_fn"

    def test_exception_propagates(self, recording_handler: RecordingHandler) -> None:
        """Exceptions from the decorated function propagate and set error field."""
        px.init()
        px.add_handler(recording_handler)

        @observe()
        def boom() -> None:
            raise ValueError("kaboom")

        with pytest.raises(ValueError, match="kaboom"):
            boom()

        px.flush()
        obs = recording_handler.observe_spans[0]
        assert obs.error == "ValueError"

    def test_noop_without_init(self) -> None:
        """@observe works normally when init() has not been called."""

        # Do NOT call px.init()
        @observe()
        def double(x: int) -> int:
            return x * 2

        assert double(21) == 42

    def test_complex_input_serialized(
        self, recording_handler: RecordingHandler
    ) -> None:
        """Complex input types are serialized via jsonpickle."""
        px.init()
        px.add_handler(recording_handler)

        @observe()
        def process(data: dict, items: list) -> str:  # type: ignore[type-arg]
            return "done"

        process({"key": "value"}, [1, 2, 3])
        px.flush()

        obs = recording_handler.observe_spans[0]
        # Input should be a JSON string containing the function arguments
        assert "key" in obs.input
        assert "value" in obs.input

    def test_positional_args_captured(
        self, recording_handler: RecordingHandler
    ) -> None:
        """Positional arguments are captured by binding to the signature."""
        px.init()
        px.add_handler(recording_handler)

        @observe()
        def add(a: int, b: int) -> int:
            return a + b

        result = add(3, 4)
        px.flush()

        assert result == 7
        obs = recording_handler.observe_spans[0]
        # Both positional args should appear in the serialized input
        assert "a" in obs.input
        assert "b" in obs.input

    def test_self_excluded_from_input(
        self, recording_handler: RecordingHandler
    ) -> None:
        """@observe on a method strips 'self' from captured input."""
        px.init()
        px.add_handler(recording_handler)

        class Agent:
            secret_key = "sk-SHOULD-NOT-APPEAR"

            @observe()
            def respond(self, message: str) -> str:
                return f"Got: {message}"

        agent = Agent()
        result = agent.respond("hello")
        px.flush()

        assert result == "Got: hello"
        obs = recording_handler.observe_spans[0]
        assert "hello" in obs.input
        assert "self" not in obs.input
        assert "sk-SHOULD-NOT-APPEAR" not in obs.input

    def test_cls_excluded_from_input(self, recording_handler: RecordingHandler) -> None:
        """@observe on a classmethod strips 'cls' from captured input."""
        px.init()
        px.add_handler(recording_handler)

        class Service:
            api_key = "sk-SECRET"

            @classmethod
            @observe()
            def handle(cls, query: str) -> str:
                return f"Handled: {query}"

        result = Service.handle("test")
        px.flush()

        assert result == "Handled: test"
        obs = recording_handler.observe_spans[0]
        assert "test" in obs.input
        assert "cls" not in obs.input
        assert "sk-SECRET" not in obs.input
