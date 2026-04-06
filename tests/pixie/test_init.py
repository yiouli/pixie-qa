"""Tests for ``pixie`` root package public API re-exports.

Every symbol that users should be able to ``from pixie import X`` must be
verified here — if it's not re-exported from ``pixie/__init__.py``, the
test fails.
"""

from __future__ import annotations


class TestRootPackageExports:
    """All user-facing symbols must be importable from ``pixie``."""

    # -- Instrumentation API --

    def test_flush(self) -> None:
        from pixie import flush

        assert callable(flush)

    def test_init(self) -> None:
        from pixie import init

        assert callable(init)

    def test_add_handler(self) -> None:
        from pixie import add_handler

        assert callable(add_handler)

    # -- Evals API --

    def test_evaluate(self) -> None:
        from pixie import evaluate

        assert callable(evaluate)

    def test_evaluation_class(self) -> None:
        from pixie import Evaluation

        assert Evaluation is not None

    def test_score_threshold(self) -> None:
        from pixie import ScoreThreshold

        assert ScoreThreshold is not None

    # -- Evaluators --

    def test_factuality_eval(self) -> None:
        from pixie import Factuality

        assert Factuality is not None

    def test_exact_match_eval(self) -> None:
        from pixie import ExactMatch

        assert ExactMatch is not None

    def test_levenshtein_match(self) -> None:
        from pixie import LevenshteinMatch

        assert LevenshteinMatch is not None

    def test_valid_json_eval(self) -> None:
        from pixie import ValidJSON

        assert ValidJSON is not None

    def test_json_diff_eval(self) -> None:
        from pixie import JSONDiff

        assert JSONDiff is not None

    def test_context_relevancy_eval(self) -> None:
        from pixie import ContextRelevancy

        assert ContextRelevancy is not None

    def test_faithfulness_eval(self) -> None:
        from pixie import Faithfulness

        assert Faithfulness is not None

    # -- Dataset / Storage --

    def test_evaluable(self) -> None:
        from pixie import Evaluable

        assert Evaluable is not None

    def test_named_data(self) -> None:
        from pixie import NamedData

        assert NamedData is not None

    def test_test_case(self) -> None:
        from pixie import TestCase

        assert TestCase is not None

    def test_unset_sentinel(self) -> None:
        from pixie import UNSET

        assert UNSET is not None

    # -- Wrap API --

    def test_wrap(self) -> None:
        from pixie import wrap

        assert callable(wrap)
