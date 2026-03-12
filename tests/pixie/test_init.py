"""Tests for ``pixie`` root package public API re-exports.

Every symbol that users should be able to ``from pixie import X`` must be
verified here — if it's not re-exported from ``pixie/__init__.py``, the
test fails.
"""

from __future__ import annotations


class TestRootPackageExports:
    """All user-facing symbols must be importable from ``pixie``."""

    # -- Instrumentation API --

    def test_enable_storage(self) -> None:
        from pixie import enable_storage

        assert callable(enable_storage)

    def test_observe(self) -> None:
        from pixie import observe

        assert callable(observe)

    def test_start_observation(self) -> None:
        from pixie import start_observation

        assert callable(start_observation)

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

    def test_assert_dataset_pass(self) -> None:
        from pixie import assert_dataset_pass

        assert callable(assert_dataset_pass)

    def test_assert_pass(self) -> None:
        from pixie import assert_pass

        assert callable(assert_pass)

    def test_run_and_evaluate(self) -> None:
        from pixie import run_and_evaluate

        assert callable(run_and_evaluate)

    def test_evaluate(self) -> None:
        from pixie import evaluate

        assert callable(evaluate)

    def test_evaluation_class(self) -> None:
        from pixie import Evaluation

        assert Evaluation is not None

    def test_score_threshold(self) -> None:
        from pixie import ScoreThreshold

        assert ScoreThreshold is not None

    def test_eval_assertion_error(self) -> None:
        from pixie import EvalAssertionError

        assert issubclass(EvalAssertionError, Exception)

    def test_capture_traces(self) -> None:
        from pixie import capture_traces

        assert callable(capture_traces)

    def test_last_llm_call(self) -> None:
        from pixie import last_llm_call

        assert callable(last_llm_call)

    def test_root(self) -> None:
        from pixie import root

        assert callable(root)

    # -- Evaluators --

    def test_factuality_eval(self) -> None:
        from pixie import FactualityEval

        assert FactualityEval is not None

    def test_exact_match_eval(self) -> None:
        from pixie import ExactMatchEval

        assert ExactMatchEval is not None

    def test_levenshtein_match(self) -> None:
        from pixie import LevenshteinMatch

        assert LevenshteinMatch is not None

    def test_valid_json_eval(self) -> None:
        from pixie import ValidJSONEval

        assert ValidJSONEval is not None

    def test_json_diff_eval(self) -> None:
        from pixie import JSONDiffEval

        assert JSONDiffEval is not None

    def test_context_relevancy_eval(self) -> None:
        from pixie import ContextRelevancyEval

        assert ContextRelevancyEval is not None

    def test_faithfulness_eval(self) -> None:
        from pixie import FaithfulnessEval

        assert FaithfulnessEval is not None

    # -- Dataset / Storage --

    def test_dataset_store(self) -> None:
        from pixie import DatasetStore

        assert DatasetStore is not None

    def test_evaluable(self) -> None:
        from pixie import Evaluable

        assert Evaluable is not None

    def test_unset_sentinel(self) -> None:
        from pixie import UNSET

        assert UNSET is not None

    # -- Span types (helpful for custom evaluators) --

    def test_observation_store(self) -> None:
        from pixie import ObservationStore

        assert ObservationStore is not None
