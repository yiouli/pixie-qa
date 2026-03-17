"""Tests for pixie.evals.scorecard — scorecard models, collector, and HTML generation."""

from __future__ import annotations

import os
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from pixie.evals.evaluation import Evaluation
from pixie.evals.scorecard import (
    AssertRecord,
    ScorecardCollector,
    ScorecardReport,
    TestRecord,
    _describe_criteria,
    _evaluator_display_name,
    _input_label,
    _normalise_filename,
    generate_scorecard_html,
    get_active_collector,
    save_scorecard,
)

# ── Helpers ──────────────────────────────────────────────────────────────


def _make_evaluation(score: float, reasoning: str = "ok") -> Evaluation:
    return Evaluation(score=score, reasoning=reasoning)


def _make_assert_record(
    *,
    evaluator_names: tuple[str, ...] = ("EvalA",),
    input_labels: tuple[str, ...] = ("input1",),
    scores: list[list[list[float]]] | None = None,
    passed: bool = True,
    criteria_message: str = "Pass",
    scoring_strategy: str = "All scores >= 0.5",
) -> AssertRecord:
    """Build an AssertRecord with the given scores tensor."""
    if scores is None:
        scores = [[[1.0]]]
    results = [
        [[_make_evaluation(s) for s in inp_evals] for inp_evals in pass_results]
        for pass_results in scores
    ]
    return AssertRecord(
        evaluator_names=evaluator_names,
        input_labels=input_labels,
        results=results,
        passed=passed,
        criteria_message=criteria_message,
        scoring_strategy=scoring_strategy,
    )


# ── _evaluator_display_name tests ────────────────────────────────────────


class TestEvaluatorDisplayName:
    """Tests for _evaluator_display_name()."""

    def test_plain_function(self) -> None:
        def my_evaluator() -> None:
            pass

        assert _evaluator_display_name(my_evaluator) == "my_evaluator"

    def test_class_with_name_attr(self) -> None:
        class MyScorer:
            name = "CustomScorer"

        assert _evaluator_display_name(MyScorer()) == "CustomScorer"

    def test_class_without_name_attr(self) -> None:
        class MyScorer:
            pass

        assert _evaluator_display_name(MyScorer()) == "MyScorer"

    def test_prefers_name_attr_over_class_name(self) -> None:
        class MyScorer:
            name = "Preferred"

        assert _evaluator_display_name(MyScorer()) == "Preferred"


# ── _input_label tests ───────────────────────────────────────────────────


class TestInputLabel:
    """Tests for _input_label()."""

    def test_short_string(self) -> None:
        assert _input_label("hello") == "hello"

    def test_long_string_truncated(self) -> None:
        long_str = "x" * 100
        label = _input_label(long_str)
        assert len(label) == 81  # 80 + "…"
        assert label.endswith("…")

    def test_non_string_input(self) -> None:
        assert _input_label(42) == "42"


# ── _normalise_filename tests ────────────────────────────────────────────


class TestNormaliseFilename:
    """Tests for _normalise_filename()."""

    def test_simple_string(self) -> None:
        assert _normalise_filename("pixie-test") == "pixie-test"

    def test_spaces_and_special_chars(self) -> None:
        result = _normalise_filename("pixie test ./foo --verbose")
        assert " " not in result
        assert "/" not in result
        assert "." not in result

    def test_consecutive_hyphens_collapsed(self) -> None:
        result = _normalise_filename("a//b  c")
        assert "--" not in result

    def test_truncation(self) -> None:
        result = _normalise_filename("a" * 100)
        assert len(result) <= 60


# ── _describe_criteria tests ─────────────────────────────────────────────


class TestDescribeCriteria:
    """Tests for _describe_criteria()."""

    def test_score_threshold(self) -> None:
        from pixie.evals.criteria import ScoreThreshold

        desc = _describe_criteria(ScoreThreshold(threshold=0.7, pct=0.8))
        assert "0.7" in desc
        assert "80%" in desc

    def test_custom_callable(self) -> None:
        def my_criteria(results: Any) -> tuple[bool, str]:
            return (True, "ok")

        desc = _describe_criteria(my_criteria)
        assert "Custom criteria" in desc


# ── ScorecardCollector tests ─────────────────────────────────────────────


class TestScorecardCollector:
    """Tests for ScorecardCollector context-local accumulation."""

    def test_record_and_drain(self) -> None:
        collector = ScorecardCollector()
        record = _make_assert_record()
        collector.record(record)
        drained = collector.drain()
        assert len(drained) == 1
        assert drained[0] is record

    def test_drain_clears(self) -> None:
        collector = ScorecardCollector()
        collector.record(_make_assert_record())
        collector.drain()
        assert collector.drain() == []

    def test_activate_deactivate(self) -> None:
        assert get_active_collector() is None
        collector = ScorecardCollector()
        collector.activate()
        assert get_active_collector() is collector
        collector.deactivate()
        assert get_active_collector() is None

    def test_nested_collectors(self) -> None:
        outer = ScorecardCollector()
        inner = ScorecardCollector()
        outer.activate()
        assert get_active_collector() is outer
        inner.activate()
        assert get_active_collector() is inner
        inner.deactivate()
        assert get_active_collector() is outer
        outer.deactivate()
        assert get_active_collector() is None


# ── generate_scorecard_html tests ────────────────────────────────────────


class TestGenerateScorecardHtml:
    """Tests for generate_scorecard_html()."""

    def test_basic_structure(self) -> None:
        report = ScorecardReport(
            command_args="pixie test .",
            test_records=[
                TestRecord(name="test_a.py::test_one", status="passed"),
                TestRecord(name="test_b.py::test_two", status="failed", message="oops"),
            ],
            timestamp=datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        html_out = generate_scorecard_html(report)

        assert "<!DOCTYPE html>" in html_out
        assert "1/2 tests passed" in html_out
        assert "test_a.py::test_one" in html_out
        assert "test_b.py::test_two" in html_out
        assert "PASS" in html_out
        assert "FAIL" in html_out
        assert "pixie test ." in html_out

    def test_assert_records_rendered(self) -> None:
        ar = _make_assert_record(
            evaluator_names=("Levenshtein", "Factuality"),
            input_labels=("q1", "q2"),
            scores=[[[0.9, 0.8], [0.3, 0.7]]],
            passed=False,
            criteria_message="Fail: 1/2 inputs",
            scoring_strategy="Each score >= 0.5",
        )
        report = ScorecardReport(
            command_args="pixie test .",
            test_records=[
                TestRecord(
                    name="test_eval.py::test_fn",
                    status="failed",
                    message="assertion failed",
                    asserts=[ar],
                ),
            ],
        )
        html_out = generate_scorecard_html(report)

        assert "Levenshtein" in html_out
        assert "Factuality" in html_out
        assert "q1" in html_out
        assert "q2" in html_out
        assert "0.90" in html_out
        assert "0.30" in html_out
        assert "Each score &gt;= 0.5" in html_out or "Each score >= 0.5" in html_out

    def test_multi_pass_tabs(self) -> None:
        ar = _make_assert_record(
            evaluator_names=("Eval",),
            input_labels=("inp",),
            scores=[[[1.0]], [[0.5]]],
            passed=True,
        )
        report = ScorecardReport(
            command_args="pixie test .",
            test_records=[
                TestRecord(
                    name="test.py::test_multi",
                    status="passed",
                    asserts=[ar],
                ),
            ],
        )
        html_out = generate_scorecard_html(report)
        assert "Pass 1" in html_out
        assert "Pass 2" in html_out
        assert "tab-btn" in html_out

    def test_no_asserts_message(self) -> None:
        report = ScorecardReport(
            command_args="pixie test .",
            test_records=[
                TestRecord(name="test.py::test_plain", status="passed"),
            ],
        )
        html_out = generate_scorecard_html(report)
        assert "No assert_pass" in html_out

    def test_error_message_rendered(self) -> None:
        report = ScorecardReport(
            command_args="pixie test .",
            test_records=[
                TestRecord(
                    name="test.py::test_err",
                    status="error",
                    message="RuntimeError: boom",
                ),
            ],
        )
        html_out = generate_scorecard_html(report)
        assert "RuntimeError: boom" in html_out
        assert "ERROR" in html_out


# ── save_scorecard tests ─────────────────────────────────────────────────


class TestSaveScorecard:
    """Tests for save_scorecard()."""

    def test_saves_html_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path / "pixie_qa"))

        report = ScorecardReport(
            command_args="pixie test .",
            test_records=[
                TestRecord(name="test.py::test_ok", status="passed"),
            ],
            timestamp=datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        filepath = save_scorecard(report)

        assert os.path.isfile(filepath)
        assert filepath.endswith(".html")
        assert "scorecards" in filepath
        with open(filepath) as f:
            content = f.read()
        assert "<!DOCTYPE html>" in content
        assert "test.py::test_ok" in content

    def test_filename_contains_timestamp(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path / "pixie_qa"))

        report = ScorecardReport(
            command_args="pixie test .",
            test_records=[],
            timestamp=datetime(2025, 6, 15, 14, 30, 45, tzinfo=timezone.utc),
        )
        filepath = save_scorecard(report)
        filename = os.path.basename(filepath)
        assert filename.startswith("20250615-143045")


# ── Integration: assert_pass publishes to collector ──────────────────────


class TestAssertPassPublishes:
    """Integration test: assert_pass pushes records to the collector."""

    @pytest.mark.asyncio
    async def test_passing_assert_publishes(self) -> None:
        import pixie.instrumentation.observation as px
        from pixie.evals.eval_utils import assert_pass

        px._reset_state()

        async def always_pass(evaluable: Any, *, trace: Any = None) -> Evaluation:
            return Evaluation(score=1.0, reasoning="ok")

        def app(inp: Any) -> None:
            with px.start_observation(input=inp, name="app") as obs:
                obs.set_output("result")

        collector = ScorecardCollector()
        collector.activate()
        try:
            await assert_pass(
                runnable=app,
                eval_inputs=["a"],
                evaluators=[always_pass],
            )
            records = collector.drain()
            assert len(records) == 1
            assert records[0].passed is True
            assert records[0].evaluator_names == ("always_pass",)
        finally:
            collector.deactivate()

    @pytest.mark.asyncio
    async def test_failing_assert_publishes(self) -> None:
        import pixie.instrumentation.observation as px
        from pixie.evals.eval_utils import EvalAssertionError, assert_pass

        px._reset_state()

        async def always_fail(evaluable: Any, *, trace: Any = None) -> Evaluation:
            return Evaluation(score=0.0, reasoning="fail")

        def app(inp: Any) -> None:
            with px.start_observation(input=inp, name="app") as obs:
                obs.set_output("result")

        collector = ScorecardCollector()
        collector.activate()
        try:
            with pytest.raises(EvalAssertionError):
                await assert_pass(
                    runnable=app,
                    eval_inputs=["a"],
                    evaluators=[always_fail],
                )
            records = collector.drain()
            assert len(records) == 1
            assert records[0].passed is False
        finally:
            collector.deactivate()

    @pytest.mark.asyncio
    async def test_no_collector_no_error(self) -> None:
        """assert_pass works normally when no collector is active."""
        import pixie.instrumentation.observation as px
        from pixie.evals.eval_utils import assert_pass

        px._reset_state()

        async def always_pass(evaluable: Any, *, trace: Any = None) -> Evaluation:
            return Evaluation(score=1.0, reasoning="ok")

        def app(inp: Any) -> None:
            with px.start_observation(input=inp, name="app") as obs:
                obs.set_output("result")

        # Should not raise even without a collector
        await assert_pass(
            runnable=app,
            eval_inputs=["a"],
            evaluators=[always_pass],
        )


# ── Integration: runner captures assert records ──────────────────────────


class TestRunnerCapturesRecords:
    """Integration test: runner enriches EvalTestResult with assert_records."""

    def test_runner_captures_records(self, tmp_path: Path) -> None:
        from pixie.evals.runner import discover_tests, run_tests

        test_file = tmp_path / "test_sc.py"
        test_file.write_text(textwrap.dedent("""\
            import asyncio
            import pixie.instrumentation.observation as px
            from pixie.evals.eval_utils import assert_pass
            from pixie.evals.evaluation import Evaluation

            px._reset_state()

            async def always_pass(evaluable, *, trace=None):
                return Evaluation(score=1.0, reasoning="ok")

            def app(inp):
                with px.start_observation(input=inp, name="app") as obs:
                    obs.set_output("result")

            def test_with_assert():
                asyncio.run(assert_pass(
                    runnable=app,
                    eval_inputs=["a"],
                    evaluators=[always_pass],
                ))
        """))

        cases = discover_tests(str(tmp_path))
        results = run_tests(cases)
        assert len(results) == 1
        assert results[0].status == "passed"
        assert len(results[0].assert_records) == 1
        assert results[0].assert_records[0].passed is True
