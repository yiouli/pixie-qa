"""Tests for pixie.evals.eval_utils — run_and_evaluate, assert_pass, EvalAssertionError."""

from __future__ import annotations

from typing import Any

import pytest

import pixie.instrumentation as px
from pixie.evals.eval_utils import (
    EvalAssertionError,
    assert_pass,
    run_and_evaluate,
)
from pixie.evals.evaluation import Evaluation
from pixie.storage.evaluable import Evaluable, as_evaluable
from pixie.storage.tree import ObservationNode

# ── Helpers ──────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_instrumentation() -> None:
    """Reset global instrumentation state before each test."""
    px._reset_state()


def _sync_app(input: Any) -> None:  # noqa: A002
    """Sync application that produces an observe span."""
    with px.log(input=input, name="app") as span:
        span.set_output(f"echo:{input}")


async def _async_app(input: Any) -> None:  # noqa: A002
    """Async application that produces an observe span."""
    with px.log(input=input, name="app") as span:
        span.set_output(f"echo:{input}")


def _nested_app(input: Any) -> None:  # noqa: A002
    """Application that produces nested spans."""
    with px.log(input=input, name="root") as span:
        with px.log(input=input, name="generator") as child:
            child.set_output("generated")
        span.set_output("final")


async def _always_pass(
    evaluable: Evaluable,
    *,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
    return Evaluation(score=1.0, reasoning="pass")


async def _always_fail(
    evaluable: Evaluable,
    *,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
    return Evaluation(score=0.2, reasoning="fail")


async def _score_half(
    evaluable: Evaluable,
    *,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
    return Evaluation(score=0.5, reasoning="half")


# ── run_and_evaluate tests ────────────────────────────────────────────────


class TestRunAndEvaluate:
    """Tests for run_and_evaluate()."""

    @pytest.mark.asyncio
    async def test_sync_runnable(self) -> None:
        result = await run_and_evaluate(
            evaluator=_always_pass,
            runnable=_sync_app,
            input="hello",
        )
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_async_runnable(self) -> None:
        result = await run_and_evaluate(
            evaluator=_always_pass,
            runnable=_async_app,
            input="hello",
        )
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_from_trace_none_evaluates_root_span(self) -> None:
        """When from_trace is None, the root span's output is evaluated."""

        async def check_root(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            assert evaluable.eval_output == "final"
            return Evaluation(score=1.0, reasoning="ok")

        result = await run_and_evaluate(
            evaluator=check_root,
            runnable=_nested_app,
            input="q",
        )
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_from_trace_selects_specific_span(self) -> None:
        async def check_child(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            assert evaluable.eval_output == "generated"
            return Evaluation(score=1.0, reasoning="ok")

        result = await run_and_evaluate(
            evaluator=check_child,
            runnable=_nested_app,
            input="q",
            from_trace=lambda tree: as_evaluable(tree[0].find("generator")[0].span),
        )
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_trace_passed_to_evaluator(self) -> None:
        received_traces: list[list[ObservationNode] | None] = []

        async def capture_eval(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            received_traces.append(trace)
            return Evaluation(score=1.0, reasoning="ok")

        await run_and_evaluate(
            evaluator=capture_eval,
            runnable=_sync_app,
            input="hello",
        )
        assert received_traces[0] is not None
        assert len(received_traces[0]) >= 1

    @pytest.mark.asyncio
    async def test_captures_input_output(self) -> None:
        """Evaluator receives correct input/output from the runnable."""

        async def check_io(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            assert evaluable.eval_input == "world"
            assert evaluable.eval_output == "echo:world"
            return Evaluation(score=1.0, reasoning="ok")

        result = await run_and_evaluate(
            evaluator=check_io,
            runnable=_sync_app,
            input="world",
        )
        assert result.score == 1.0


# ── assert_pass tests ─────────────────────────────────────────────────────


class TestAssertPass:
    """Tests for assert_pass()."""

    @pytest.mark.asyncio
    async def test_passes_when_all_above_threshold(self) -> None:
        await assert_pass(
            runnable=_sync_app,
            inputs=["q1"],
            evaluators=[_always_pass],
        )

    @pytest.mark.asyncio
    async def test_raises_when_score_below_threshold(self) -> None:
        with pytest.raises(EvalAssertionError):
            await assert_pass(
                runnable=_sync_app,
                inputs=["q1"],
                evaluators=[_always_fail],
            )

    @pytest.mark.asyncio
    async def test_results_tensor_shape(self) -> None:
        """Shape is [1][1][2] for 1 pass, 1 input, 2 evaluators."""
        with pytest.raises(EvalAssertionError) as exc_info:
            await assert_pass(
                runnable=_sync_app,
                inputs=["q1"],
                evaluators=[_always_pass, _always_fail],
            )
        results = exc_info.value.results
        assert len(results) == 1  # 1 pass
        assert len(results[0]) == 1  # 1 input
        assert len(results[0][0]) == 2  # 2 evaluators

    @pytest.mark.asyncio
    async def test_multiple_passes(self) -> None:
        with pytest.raises(EvalAssertionError) as exc_info:
            await assert_pass(
                runnable=_sync_app,
                inputs=["q1"],
                evaluators=[_always_fail],
                passes=3,
            )
        results = exc_info.value.results
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_multiple_inputs(self) -> None:
        """Shape is [1][2][1] for 1 pass, 2 inputs, 1 evaluator."""
        await assert_pass(
            runnable=_sync_app,
            inputs=["q1", "q2"],
            evaluators=[_always_pass],
        )

    @pytest.mark.asyncio
    async def test_custom_pass_criteria(self) -> None:
        def lenient(
            results: list[list[list[Evaluation]]],
        ) -> tuple[bool, str]:
            return (True, "always passes")

        await assert_pass(
            runnable=_sync_app,
            inputs=["q1"],
            evaluators=[_always_fail],
            pass_criteria=lenient,
        )

    @pytest.mark.asyncio
    async def test_custom_from_trace(self) -> None:
        async def check_child(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            assert evaluable.eval_output == "generated"
            return Evaluation(score=1.0, reasoning="ok")

        await assert_pass(
            runnable=_nested_app,
            inputs=["q1"],
            evaluators=[check_child],
            from_trace=lambda tree: as_evaluable(tree[0].find("generator")[0].span),
        )

    @pytest.mark.asyncio
    async def test_eval_assertion_error_carries_results(self) -> None:
        with pytest.raises(EvalAssertionError) as exc_info:
            await assert_pass(
                runnable=_sync_app,
                inputs=["q1"],
                evaluators=[_always_fail],
            )
        err = exc_info.value
        assert isinstance(err, AssertionError)
        assert err.results[0][0][0].score == 0.2

    @pytest.mark.asyncio
    async def test_score_exactly_half_passes_default(self) -> None:
        """Score of exactly 0.5 passes with default criteria."""
        await assert_pass(
            runnable=_sync_app,
            inputs=["q1"],
            evaluators=[_score_half],
        )
