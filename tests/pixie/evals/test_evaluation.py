"""Tests for pixie.evals.evaluation — Evaluation, Evaluator protocol, evaluate()."""

from __future__ import annotations

from typing import Any

import pytest

from pixie.evals.evaluation import Evaluation, evaluate
from pixie.storage.evaluable import Evaluable
from pixie.storage.tree import ObservationNode

# ── Helpers ──────────────────────────────────────────────────────────────


class _StubEvaluable:
    """Minimal Evaluable for testing."""

    def __init__(
        self,
        *,
        eval_input: Any = "in",
        eval_output: Any = "out",
        eval_metadata: dict[str, Any] | None = None,
    ) -> None:
        self._input = eval_input
        self._output = eval_output
        self._metadata = eval_metadata or {}

    @property
    def eval_input(self) -> Any:
        return self._input

    @property
    def eval_output(self) -> Any:
        return self._output

    @property
    def eval_metadata(self) -> dict[str, Any]:
        return self._metadata


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

        result = await evaluate(my_eval, _StubEvaluable())
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

        result = await evaluate(my_eval, _StubEvaluable())
        assert result.score == 0.7
        assert result.reasoning == "sync works"

    @pytest.mark.asyncio
    async def test_evaluator_exception_returns_zero_with_error(self) -> None:
        async def failing_eval(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            raise ValueError("boom")

        result = await evaluate(failing_eval, _StubEvaluable())
        assert result.score == 0.0
        assert "boom" in result.reasoning
        assert result.details.get("error") == "ValueError"
        assert "traceback" in result.details

    @pytest.mark.asyncio
    async def test_clamps_score_above_one(self) -> None:
        async def over_score(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            return Evaluation(score=1.5, reasoning="too high")

        result = await evaluate(over_score, _StubEvaluable())
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_clamps_score_below_zero(self) -> None:
        async def under_score(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            return Evaluation(score=-0.3, reasoning="too low")

        result = await evaluate(under_score, _StubEvaluable())
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

        await evaluate(trace_eval, _StubEvaluable(), trace=[])
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

        result = await evaluate(MyEval(), _StubEvaluable())
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
            _StubEvaluable(eval_input="hello", eval_output="world"),
        )

    @pytest.mark.asyncio
    async def test_expected_output_forwarded_to_evaluator(self) -> None:
        """evaluate() passes expected_output kwarg to the evaluator."""
        received: list[Any] = []

        async def capture_eval(
            evaluable: Evaluable,
            *,
            expected_output: Any = None,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            received.append(expected_output)
            return Evaluation(score=1.0, reasoning="ok")

        await evaluate(capture_eval, _StubEvaluable(), expected_output="ground truth")
        assert received == ["ground truth"]

    @pytest.mark.asyncio
    async def test_expected_output_none_by_default(self) -> None:
        """When expected_output is not provided, evaluator gets None."""
        received: list[Any] = []

        async def capture_eval(
            evaluable: Evaluable,
            *,
            expected_output: Any = None,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            received.append(expected_output)
            return Evaluation(score=1.0, reasoning="ok")

        await evaluate(capture_eval, _StubEvaluable())
        assert received == [None]

    @pytest.mark.asyncio
    async def test_expected_output_works_with_sync_evaluator(self) -> None:
        """Sync evaluators also receive expected_output correctly."""
        received: list[Any] = []

        def sync_eval(
            evaluable: Evaluable,
            *,
            expected_output: Any = None,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            received.append(expected_output)
            return Evaluation(score=1.0, reasoning="sync ok")

        result = await evaluate(sync_eval, _StubEvaluable(), expected_output="expected")
        assert result.score == 1.0
        assert received == ["expected"]
