"""Tests for pixie.evals.eval_utils — run_and_evaluate, assert_pass, assert_dataset_pass."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import pixie.instrumentation.observation as px
from pixie.dataset.store import DatasetStore
from pixie.evals.eval_utils import (
    EvalAssertionError,
    assert_dataset_pass,
    assert_pass,
    run_and_evaluate,
)
from pixie.evals.evaluation import Evaluation
from pixie.storage.evaluable import UNSET, Evaluable, as_evaluable
from pixie.storage.tree import ObservationNode

# ── Helpers ──────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_instrumentation() -> None:
    """Reset global instrumentation state before each test."""
    px._reset_state()


def _sync_app(input: Any) -> None:  # noqa: A002
    """Sync application that produces an observe span."""
    with px.start_observation(input=input, name="app") as observation:
        observation.set_output(f"echo:{input}")


async def _async_app(input: Any) -> None:  # noqa: A002
    """Async application that produces an observe span."""
    with px.start_observation(input=input, name="app") as observation:
        observation.set_output(f"echo:{input}")


def _nested_app(input: Any) -> None:  # noqa: A002
    """Application that produces nested spans."""
    with px.start_observation(input=input, name="root") as observation:
        with px.start_observation(input=input, name="generator") as child:
            child.set_output("generated")
        observation.set_output("final")


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
            eval_input="hello",
        )
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_async_runnable(self) -> None:
        result = await run_and_evaluate(
            evaluator=_always_pass,
            runnable=_async_app,
            eval_input="hello",
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
            eval_input="q",
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
            eval_input="q",
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
            eval_input="hello",
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
            eval_input="world",
        )
        assert result.score == 1.0


# ── run_and_evaluate expected_output tests ────────────────────────────────


class TestRunAndEvaluateExpectedOutput:
    """Tests for expected_output parameter in run_and_evaluate()."""

    @pytest.mark.asyncio
    async def test_expected_output_merged_into_evaluable(self) -> None:
        """expected_output is merged into the span-derived evaluable."""
        received: list[Any] = []

        async def capture_eval(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            received.append(evaluable.expected_output)
            return Evaluation(score=1.0, reasoning="ok")

        await run_and_evaluate(
            evaluator=capture_eval,
            runnable=_sync_app,
            eval_input="hello",
            expected_output="expected_val",
        )
        assert received == ["expected_val"]

    @pytest.mark.asyncio
    async def test_expected_output_unset_by_default(self) -> None:
        """Without expected_output, evaluable has UNSET."""
        received: list[Any] = []

        async def capture_eval(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            received.append(evaluable.expected_output)
            return Evaluation(score=1.0, reasoning="ok")

        await run_and_evaluate(
            evaluator=capture_eval,
            runnable=_sync_app,
            eval_input="hello",
        )
        assert received[0] is UNSET

    @pytest.mark.asyncio
    async def test_expected_output_none_is_explicit(self) -> None:
        """Passing expected_output=None sets it explicitly (not UNSET)."""
        received: list[Any] = []

        async def capture_eval(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            received.append(evaluable.expected_output)
            return Evaluation(score=1.0, reasoning="ok")

        await run_and_evaluate(
            evaluator=capture_eval,
            runnable=_sync_app,
            eval_input="hello",
            expected_output=None,
        )
        assert received == [None]

    @pytest.mark.asyncio
    async def test_expected_output_preserves_span_data(self) -> None:
        """Merging expected_output preserves the span's input/output."""

        async def check_all(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            assert evaluable.eval_input == "test"
            assert evaluable.eval_output == "echo:test"
            assert evaluable.expected_output == "ref"
            return Evaluation(score=1.0, reasoning="ok")

        result = await run_and_evaluate(
            evaluator=check_all,
            runnable=_sync_app,
            eval_input="test",
            expected_output="ref",
        )
        assert result.score == 1.0


# ── assert_pass tests ─────────────────────────────────────────────────────


class TestAssertPass:
    """Tests for assert_pass()."""

    @pytest.mark.asyncio
    async def test_passes_when_all_above_threshold(self) -> None:
        await assert_pass(
            runnable=_sync_app,
            eval_inputs=["q1"],
            evaluators=[_always_pass],
        )

    @pytest.mark.asyncio
    async def test_raises_when_score_below_threshold(self) -> None:
        with pytest.raises(EvalAssertionError):
            await assert_pass(
                runnable=_sync_app,
                eval_inputs=["q1"],
                evaluators=[_always_fail],
            )

    @pytest.mark.asyncio
    async def test_results_tensor_shape(self) -> None:
        """Shape is [1][1][2] for 1 pass, 1 input, 2 evaluators."""
        with pytest.raises(EvalAssertionError) as exc_info:
            await assert_pass(
                runnable=_sync_app,
                eval_inputs=["q1"],
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
                eval_inputs=["q1"],
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
            eval_inputs=["q1", "q2"],
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
            eval_inputs=["q1"],
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
            eval_inputs=["q1"],
            evaluators=[check_child],
            from_trace=lambda tree: as_evaluable(tree[0].find("generator")[0].span),
        )

    @pytest.mark.asyncio
    async def test_eval_assertion_error_carries_results(self) -> None:
        with pytest.raises(EvalAssertionError) as exc_info:
            await assert_pass(
                runnable=_sync_app,
                eval_inputs=["q1"],
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
            eval_inputs=["q1"],
            evaluators=[_score_half],
        )


# ── evaluables parameter tests ────────────────────────────────────────────


class TestAssertPassEvaluables:
    """Tests for the evaluables parameter in assert_pass()."""

    @pytest.mark.asyncio
    async def test_evaluables_used_directly(self) -> None:
        """When evaluables is provided, evaluators receive them directly."""
        received: list[Any] = []

        async def capture_eval(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            received.append(evaluable.expected_output)
            return Evaluation(score=1.0, reasoning="ok")

        items = [
            Evaluable(eval_input="q1", expected_output="e1"),
            Evaluable(eval_input="q2", expected_output="e2"),
        ]
        await assert_pass(
            runnable=_sync_app,
            eval_inputs=["q1", "q2"],
            evaluators=[capture_eval],
            evaluables=items,
        )
        assert received == ["e1", "e2"]

    @pytest.mark.asyncio
    async def test_evaluables_length_mismatch_raises(self) -> None:
        """ValueError when len(evaluables) != len(eval_inputs)."""
        with pytest.raises(ValueError, match="evaluables.*length"):
            await assert_pass(
                runnable=_sync_app,
                eval_inputs=["q1", "q2"],
                evaluators=[_always_pass],
                evaluables=[Evaluable(eval_input="q1")],
            )

    @pytest.mark.asyncio
    async def test_evaluables_none_uses_trace(self) -> None:
        """When evaluables is None, evaluable is built from trace."""
        received_outputs: list[Any] = []

        async def capture_eval(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            received_outputs.append(evaluable.eval_output)
            return Evaluation(score=1.0, reasoning="ok")

        await assert_pass(
            runnable=_sync_app,
            eval_inputs=["hello"],
            evaluators=[capture_eval],
        )
        assert received_outputs == ["echo:hello"]


# ── assert_dataset_pass tests ─────────────────────────────────────────────


class TestAssertDatasetPass:
    """Tests for assert_dataset_pass()."""

    @pytest.mark.asyncio
    async def test_loads_dataset_and_evaluates(self, tmp_path: Path) -> None:
        """Loads dataset by name, maps items to inputs and evaluables."""
        store = DatasetStore(dataset_dir=tmp_path)
        store.create(
            "test-ds",
            items=[
                Evaluable(eval_input="q1", expected_output="e1"),
                Evaluable(eval_input="q2", expected_output="e2"),
            ],
        )
        received: list[Any] = []

        async def capture_eval(
            evaluable: Evaluable,
            *,
            trace: list[ObservationNode] | None = None,
        ) -> Evaluation:
            received.append(evaluable.expected_output)
            return Evaluation(score=1.0, reasoning="ok")

        await assert_dataset_pass(
            runnable=_sync_app,
            dataset_name="test-ds",
            evaluators=[capture_eval],
            dataset_dir=str(tmp_path),
        )
        assert received == ["e1", "e2"]

    @pytest.mark.asyncio
    async def test_raises_when_dataset_missing(self, tmp_path: Path) -> None:
        """FileNotFoundError when dataset does not exist."""
        with pytest.raises(FileNotFoundError):
            await assert_dataset_pass(
                runnable=_sync_app,
                dataset_name="nonexistent",
                evaluators=[_always_pass],
                dataset_dir=str(tmp_path),
            )

    @pytest.mark.asyncio
    async def test_raises_eval_assertion_on_failure(self, tmp_path: Path) -> None:
        """EvalAssertionError when evaluator scores fail."""
        store = DatasetStore(dataset_dir=tmp_path)
        store.create(
            "fail-ds",
            items=[Evaluable(eval_input="q1", expected_output="e1")],
        )
        with pytest.raises(EvalAssertionError):
            await assert_dataset_pass(
                runnable=_sync_app,
                dataset_name="fail-ds",
                evaluators=[_always_fail],
                dataset_dir=str(tmp_path),
            )

    @pytest.mark.asyncio
    async def test_passes_dataset_dir_override(self, tmp_path: Path) -> None:
        """dataset_dir overrides the default config."""
        custom_dir = tmp_path / "custom"
        store = DatasetStore(dataset_dir=custom_dir)
        store.create("custom-ds", items=[Evaluable(eval_input="q1")])

        await assert_dataset_pass(
            runnable=_sync_app,
            dataset_name="custom-ds",
            evaluators=[_always_pass],
            dataset_dir=str(custom_dir),
        )

    @pytest.mark.asyncio
    async def test_multiple_passes(self, tmp_path: Path) -> None:
        """passes parameter is forwarded."""
        store = DatasetStore(dataset_dir=tmp_path)
        store.create("multi-ds", items=[Evaluable(eval_input="q1")])
        with pytest.raises(EvalAssertionError) as exc_info:
            await assert_dataset_pass(
                runnable=_sync_app,
                dataset_name="multi-ds",
                evaluators=[_always_fail],
                dataset_dir=str(tmp_path),
                passes=3,
            )
        assert len(exc_info.value.results) == 3
