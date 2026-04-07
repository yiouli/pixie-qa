"""Tests for the Runnable protocol and utilities."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from pixie.harness.runnable import get_runnable_args_type, is_runnable_class

# ── Test Fixtures ───────────────────────────────────────────────────────────


class SampleArgs(BaseModel):
    question: str
    context: str = ""


class SampleRunnable:
    """A valid Runnable implementation for testing."""

    @classmethod
    def create(cls) -> SampleRunnable:
        return cls()

    async def setup(self) -> None:
        pass

    async def teardown(self) -> None:
        pass

    async def run(self, args: SampleArgs) -> None:
        pass


class NotARunnable:
    """A class that does NOT implement the Runnable protocol."""

    def do_something(self) -> None:
        pass


class MissingAnnotation:
    """A class with ``run`` but no type annotation on args."""

    @classmethod
    def create(cls) -> MissingAnnotation:
        return cls()

    async def run(self, args: Any) -> None:  # type: ignore[override]
        pass


class WrongAnnotation:
    """A class with ``run`` but args is not a BaseModel subclass."""

    @classmethod
    def create(cls) -> WrongAnnotation:
        return cls()

    async def run(self, args: str) -> None:  # type: ignore[override]
        pass


# ── Tests ───────────────────────────────────────────────────────────────────


class TestIsRunnableClass:
    def test_valid_runnable_class(self) -> None:
        assert is_runnable_class(SampleRunnable) is True

    def test_not_a_class(self) -> None:
        assert is_runnable_class(lambda: None) is False

    def test_missing_run_method(self) -> None:
        assert is_runnable_class(NotARunnable) is False

    def test_instance_not_class(self) -> None:
        assert is_runnable_class(SampleRunnable()) is False


class TestGetRunnableArgsType:
    def test_extracts_correct_type(self) -> None:
        result = get_runnable_args_type(SampleRunnable)
        assert result is SampleArgs

    def test_no_run_method_raises(self) -> None:
        with pytest.raises(TypeError, match="does not have a 'run' method"):
            get_runnable_args_type(NotARunnable)  # type: ignore[arg-type]

    def test_wrong_annotation_raises(self) -> None:
        with pytest.raises(TypeError, match="must be a BaseModel subclass"):
            get_runnable_args_type(WrongAnnotation)  # type: ignore[arg-type]


class TestRunnableLifecycle:
    @pytest.mark.asyncio
    async def test_create_setup_run_teardown(self) -> None:
        """Full lifecycle works end-to-end."""
        instance = SampleRunnable.create()
        await instance.setup()
        args = SampleArgs(question="test?")
        await instance.run(args)
        await instance.teardown()

    @pytest.mark.asyncio
    async def test_args_validation(self) -> None:
        """Pydantic validation works for Runnable args."""
        args_type = get_runnable_args_type(SampleRunnable)
        args = args_type.model_validate({"question": "hello"})
        assert isinstance(args, SampleArgs)
        assert args.question == "hello"
        assert args.context == ""
