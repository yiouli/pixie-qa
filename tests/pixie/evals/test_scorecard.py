"""Tests for pixie.evals.scorecard — evaluator display name and filename helpers."""

from __future__ import annotations

from pixie.evals.scorecard import (
    _evaluator_display_name,
    _normalise_filename,
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
