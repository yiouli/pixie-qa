"""Tests for pixie.evals.evaluation — Evaluation, Evaluator protocol, evaluate()."""

from __future__ import annotations

from typing import Any

import pytest

from pixie.evals.evaluation import Evaluation, evaluate
from pixie.storage.evaluable import Evaluable
from pixie.storage.tree import ObservationNode

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
        async def my_eval(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            return Evaluation(score=0.9, reasoning="async works")

        result = await evaluate(my_eval, Evaluable(eval_input="in", eval_output="out"))
        assert result.score == 0.9
        assert result.reasoning == "async works"

    @pytest.mark.asyncio
    async def test_sync_evaluator_is_wrapped(self) -> None:
        def my_eval(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            return Evaluation(score=0.7, reasoning="sync works")

        result = await evaluate(my_eval, Evaluable(eval_input="in", eval_output="out"))
        assert result.score == 0.7
        assert result.reasoning == "sync works"

    @pytest.mark.asyncio
    async def test_evaluator_exception_propagates(self) -> None:
        async def failing_eval(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            await evaluate(failing_eval, Evaluable())

    @pytest.mark.asyncio
    async def test_sync_evaluator_exception_propagates(self) -> None:
        def failing_sync_eval(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            raise RuntimeError("missing API key")

        with pytest.raises(RuntimeError, match="missing API key"):
            await evaluate(failing_sync_eval, Evaluable())

    @pytest.mark.asyncio
    async def test_clamps_score_above_one(self) -> None:
        async def over_score(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            return Evaluation(score=1.5, reasoning="too high")

        result = await evaluate(over_score, Evaluable())
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_clamps_score_below_zero(self) -> None:
        async def under_score(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            return Evaluation(score=-0.3, reasoning="too low")

        result = await evaluate(under_score, Evaluable())
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_trace_passed_through(self) -> None:
        received_trace: list[list[ObservationNode] | None] = []

        async def trace_eval(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            received_trace.append(trace)
            return Evaluation(score=1.0, reasoning="ok")

        await evaluate(trace_eval, Evaluable(), trace=[])
        assert received_trace == [[]]

    @pytest.mark.asyncio
    async def test_class_evaluator(self) -> None:
        class MyEval:
            async def __call__(
                self,
                evaluable: Evaluable,
                *,
                trace: list[ObservationNode] | None = None,
            ) -> Evaluation:
                return Evaluation(score=0.6, reasoning="class eval")

        result = await evaluate(MyEval(), Evaluable())
        assert result.score == 0.6
        assert result.reasoning == "class eval"

    @pytest.mark.asyncio
    async def test_evaluable_data_passed_correctly(self) -> None:
        async def check_data(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            assert evaluable.eval_input == "hello"
            assert evaluable.eval_output == "world"
            return Evaluation(score=1.0, reasoning="ok")

        await evaluate(
            check_data,
            Evaluable(eval_input="hello", eval_output="world"),
        )

    @pytest.mark.asyncio
    async def test_expected_output_accessible_on_evaluable(self) -> None:
        """Evaluator can read expected_output from the evaluable directly."""
        received: list[Any] = []

        async def capture_eval(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            received.append(evaluable.expected_output)
            return Evaluation(score=1.0, reasoning="ok")

        await evaluate(
            capture_eval,
            Evaluable(expected_output="ground truth"),
        )
        assert received == ["ground truth"]
