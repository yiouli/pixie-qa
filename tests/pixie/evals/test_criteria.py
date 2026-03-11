"""Tests for pixie.evals.criteria — ScoreThreshold."""

from __future__ import annotations

from pixie.evals.criteria import ScoreThreshold
from pixie.evals.evaluation import Evaluation


def _eval(score: float) -> Evaluation:
    return Evaluation(score=score, reasoning="test")


class TestScoreThresholdDefaults:
    """ScoreThreshold with default params (threshold=0.5, pct=1.0)."""

    def test_all_scores_above_threshold_passes(self) -> None:
        # 1 pass, 3 inputs, 1 evaluator each, all >= 0.5
        results = [[[_eval(0.5)], [_eval(0.8)], [_eval(1.0)]]]
        passed, msg = ScoreThreshold()(results)
        assert passed is True
        assert "Pass" in msg

    def test_one_score_below_threshold_fails(self) -> None:
        # 1 pass, 3 inputs, 1 evaluator each, one < 0.5
        results = [[[_eval(0.5)], [_eval(0.4)], [_eval(1.0)]]]
        passed, msg = ScoreThreshold()(results)
        assert passed is False
        assert "Fail" in msg


class TestScoreThresholdCustomThreshold:
    """ScoreThreshold with custom threshold."""

    def test_scores_between_05_and_07_fail_at_07(self) -> None:
        results = [[[_eval(0.6)], [_eval(0.55)]]]
        passed, _msg = ScoreThreshold(threshold=0.7)(results)
        assert passed is False

    def test_scores_at_07_pass_at_07(self) -> None:
        results = [[[_eval(0.7)], [_eval(0.9)]]]
        passed, _msg = ScoreThreshold(threshold=0.7)(results)
        assert passed is True


class TestScoreThresholdPct:
    """ScoreThreshold with pct < 1.0."""

    def test_80pct_of_inputs_pass_at_80pct(self) -> None:
        # 1 pass, 10 inputs: 8 pass, 2 fail -> 80% meets 80%
        evals = [[_eval(0.9)] for _ in range(8)] + [[_eval(0.1)] for _ in range(2)]
        results = [evals]
        passed, _msg = ScoreThreshold(pct=0.8)(results)
        assert passed is True

    def test_70pct_of_inputs_fail_at_80pct(self) -> None:
        # 1 pass, 10 inputs: 7 pass, 3 fail -> 70% < 80%
        evals = [[_eval(0.9)] for _ in range(7)] + [[_eval(0.1)] for _ in range(3)]
        results = [evals]
        passed, _msg = ScoreThreshold(pct=0.8)(results)
        assert passed is False


class TestScoreThresholdMultiplePasses:
    """Multiple passes: at-least-one-pass semantics."""

    def test_first_pass_fails_second_meets_criteria_passes(self) -> None:
        # Pass 1: all fail; Pass 2: all pass
        pass1 = [[_eval(0.1)], [_eval(0.2)]]
        pass2 = [[_eval(0.8)], [_eval(0.9)]]
        results = [pass1, pass2]
        passed, msg = ScoreThreshold()(results)
        assert passed is True
        assert "pass 2/2" in msg

    def test_no_pass_meets_criteria_fails_with_best_pass(self) -> None:
        # Pass 1: 1/2 pass; Pass 2: 0/2 pass; Pass 3: 1/2 pass
        pass1 = [[_eval(0.8)], [_eval(0.3)]]
        pass2 = [[_eval(0.1)], [_eval(0.2)]]
        pass3 = [[_eval(0.9)], [_eval(0.4)]]
        results = [pass1, pass2, pass3]
        passed, msg = ScoreThreshold()(results)
        assert passed is False
        assert "Fail" in msg
        assert "best pass" in msg


class TestScoreThresholdMessageFormat:
    """Message format includes pass number, input counts, and percentage."""

    def test_pass_message_format(self) -> None:
        results = [[[_eval(0.8)], [_eval(0.9)]]]
        _passed, msg = ScoreThreshold()(results)
        assert "pass 1/1" in msg
        assert "2/2 inputs" in msg
        assert "100.0%" in msg
        assert "scored >= 0.5" in msg
        assert "required: 100.0%" in msg

    def test_fail_message_format(self) -> None:
        pass1 = [[_eval(0.8)], [_eval(0.3)]]
        results = [pass1]
        _passed, msg = ScoreThreshold()(results)
        assert "Fail" in msg
        assert "1/2 inputs" in msg
        assert "50.0%" in msg

    def test_multiple_evaluators_per_input(self) -> None:
        # 2 evaluators per input, one fails -> that input doesn't count
        results = [[[_eval(0.8), _eval(0.3)], [_eval(0.9), _eval(0.7)]]]
        passed, _msg = ScoreThreshold()(results)
        assert passed is False  # Only 1/2 inputs pass, need 100%

    def test_multiple_evaluators_all_pass(self) -> None:
        results = [[[_eval(0.8), _eval(0.6)], [_eval(0.9), _eval(0.7)]]]
        passed, _msg = ScoreThreshold()(results)
        assert passed is True
