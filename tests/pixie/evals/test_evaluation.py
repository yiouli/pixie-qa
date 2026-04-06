"""Tests for pixie.evals.evaluation — Evaluation, Evaluator protocol, evaluate()."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import JsonValue

from pixie.evals.evaluation import Evaluation, evaluate
from pixie.storage.evaluable import Evaluable, NamedData


def _nd(name: str, value: JsonValue) -> NamedData:
    """Shorthand for creating a NamedData instance in tests."""
    return NamedData(name=name, value=value)


def _ev(
    *,
    inp: JsonValue = None,
    out: JsonValue = None,
    expectation: JsonValue | None = None,
) -> Evaluable:
    """Shorthand for creating an Evaluable with single input/output."""
    kwargs: dict[str, JsonValue | list[NamedData]] = {
        "eval_input": [_nd("input", inp)],
        "eval_output": [_nd("output", out)],
    }
    if expectation is not None:
        kwargs["expectation"] = expectation
    return Evaluable(**kwargs)  # type: ignore[arg-type]


# ── Evaluation dataclass tests ───────────────────────────────────────────


class TestEvaluation:
    """Tests for the Evaluation frozen dataclass."""

    def test_basic_construction(self) -> None:
        ev = Evaluation(score=0.8, reasoning="Good")
        assert ev.score == 0.8
        assert ev.reasoning == "Good"
        assert ev.details == {}

    def test_details_construction(self) -> None:
        ev = Evaluation(score=0.5, reasoning="ok", details={"key": "val"})
        assert ev.details == {"key": "val"}

    def test_frozen(self) -> None:
        ev = Evaluation(score=0.5, reasoning="ok")
        with pytest.raises(AttributeError):
            ev.score = 0.9  # type: ignore[misc]

    def test_score_boundary_zero(self) -> None:
        ev = Evaluation(score=0.0, reasoning="zero")
        assert ev.score == 0.0

    def test_score_boundary_one(self) -> None:
        ev = Evaluation(score=1.0, reasoning="perfect")
        assert ev.score == 1.0


# ── evaluate() tests ─────────────────────────────────────────────────────


class TestEvaluate:
    """Tests for the evaluate() function."""

    @pytest.mark.asyncio
    async def test_async_evaluator_returns_correctly(self) -> None:
        async def my_eval(evaluable: Evaluable) -> Evaluation:
            return Evaluation(score=0.9, reasoning="async works")

        result = await evaluate(my_eval, _ev(inp="in", out="out"))
        assert result.score == 0.9
        assert result.reasoning == "async works"

    @pytest.mark.asyncio
    async def test_sync_evaluator_is_wrapped(self) -> None:
        def my_eval(evaluable: Evaluable) -> Evaluation:
            return Evaluation(score=0.7, reasoning="sync works")

        result = await evaluate(my_eval, _ev(inp="in", out="out"))
        assert result.score == 0.7
        assert result.reasoning == "sync works"

    @pytest.mark.asyncio
    async def test_evaluator_exception_propagates(self) -> None:
        async def failing_eval(evaluable: Evaluable) -> Evaluation:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            await evaluate(failing_eval, _ev())

    @pytest.mark.asyncio
    async def test_sync_evaluator_exception_propagates(self) -> None:
        def failing_sync_eval(evaluable: Evaluable) -> Evaluation:
            raise RuntimeError("missing API key")

        with pytest.raises(RuntimeError, match="missing API key"):
            await evaluate(failing_sync_eval, _ev())

    @pytest.mark.asyncio
    async def test_clamps_score_above_one(self) -> None:
        async def over_score(evaluable: Evaluable) -> Evaluation:
            return Evaluation(score=1.5, reasoning="too high")

        result = await evaluate(over_score, _ev())
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_clamps_score_below_zero(self) -> None:
        async def under_score(evaluable: Evaluable) -> Evaluation:
            return Evaluation(score=-0.3, reasoning="too low")

        result = await evaluate(under_score, _ev())
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_class_evaluator(self) -> None:
        class MyEval:
            async def __call__(self, evaluable: Evaluable) -> Evaluation:
                return Evaluation(score=0.6, reasoning="class eval")

        result = await evaluate(MyEval(), _ev())
        assert result.score == 0.6
        assert result.reasoning == "class eval"

    @pytest.mark.asyncio
    async def test_evaluable_data_passed_correctly(self) -> None:
        async def check_data(evaluable: Evaluable) -> Evaluation:
            assert evaluable.eval_input[0].value == "hello"
            assert evaluable.eval_output[0].value == "world"
            return Evaluation(score=1.0, reasoning="ok")

        await evaluate(
            check_data,
            _ev(inp="hello", out="world"),
        )

    @pytest.mark.asyncio
    async def test_expectation_accessible_on_evaluable(self) -> None:
        """Evaluator can read expectation from the evaluable directly."""
        received: list[Any] = []

        async def capture_eval(evaluable: Evaluable) -> Evaluation:
            received.append(evaluable.expectation)
            return Evaluation(score=1.0, reasoning="ok")

        await evaluate(
            capture_eval,
            _ev(expectation="ground truth"),
        )
        assert received == ["ground truth"]
