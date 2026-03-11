"""Tests for pixie.evals.scorers — autoevals adapter and pre-made evaluators."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autoevals.score import Score as _AEScore
from autoevals.score import Scorer as _AEScorer

from pixie.evals.evaluation import Evaluation
from pixie.evals.scorers import (
    AnswerCorrectnessEval,
    AnswerRelevancyEval,
    AutoevalsAdapter,
    BattleEval,
    ClosedQAEval,
    ContextRelevancyEval,
    EmbeddingSimilarityEval,
    ExactMatchEval,
    FactualityEval,
    FaithfulnessEval,
    HumorEval,
    JSONDiffEval,
    LevenshteinMatch,
    ListContainsEval,
    ModerationEval,
    NumericDiffEval,
    PossibleEval,
    SecurityEval,
    SqlEval,
    SummaryEval,
    TranslationEval,
    ValidJSONEval,
    _score_to_evaluation,
)
from pixie.storage.evaluable import Evaluable

# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


@dataclass
class FakeScore(_AEScore):
    """Score subclass with convenient defaults for testing."""

    name: str = "FakeScorer"
    score: float | None = 0.85
    metadata: dict[str, Any] = field(default_factory=dict)


class FakeScorer(_AEScorer):
    """Controllable Scorer subclass for testing."""

    def __init__(self, return_score: _AEScore | None = None) -> None:
        self._return_score = return_score or FakeScore()
        self.last_call_kwargs: dict[str, Any] = {}

    def _run_eval_sync(self, output: Any, expected: Any = None, **kwargs: Any) -> _AEScore:
        self.last_call_kwargs = {"output": output, "expected": expected, **kwargs}
        return self._return_score

    async def _run_eval_async(self, output: Any, expected: Any = None, **kwargs: Any) -> _AEScore:
        self.last_call_kwargs = {"output": output, "expected": expected, **kwargs}
        return self._return_score


class RaisingScorer(_AEScorer):
    """A scorer that always raises on evaluation."""

    def _run_eval_sync(self, output: Any, expected: Any = None, **kwargs: Any) -> _AEScore:
        raise ValueError("scorer exploded")

    async def _run_eval_async(self, output: Any, expected: Any = None, **kwargs: Any) -> _AEScore:
        raise ValueError("scorer exploded")


# ---------------------------------------------------------------------------
# _score_to_evaluation
# ---------------------------------------------------------------------------


class TestScoreToEvaluation:
    """Tests for the Score → Evaluation conversion function."""

    def test_basic_conversion(self) -> None:
        score = FakeScore(name="MyScorer", score=0.75, metadata={"foo": "bar"})
        evaluation = _score_to_evaluation(score)

        assert evaluation.score == 0.75
        assert evaluation.details["foo"] == "bar"
        assert evaluation.details["scorer_name"] == "MyScorer"

    def test_rationale_used_as_reasoning(self) -> None:
        score = FakeScore(
            name="LLMJudge",
            score=1.0,
            metadata={"rationale": "Output is factually correct.", "choice": "A"},
        )
        evaluation = _score_to_evaluation(score)

        assert evaluation.reasoning == "Output is factually correct."
        assert evaluation.details["choice"] == "A"

    def test_no_rationale_generates_default_reasoning(self) -> None:
        score = FakeScore(name="Levenshtein", score=0.91, metadata={})
        evaluation = _score_to_evaluation(score)

        assert evaluation.reasoning == "Levenshtein: 0.91"

    def test_none_score_maps_to_zero(self) -> None:
        score = FakeScore(name="Skipped", score=None, metadata={})
        evaluation = _score_to_evaluation(score)

        assert evaluation.score == 0.0
        assert "skipped" in evaluation.reasoning.lower()

    def test_empty_rationale_falls_back_to_default(self) -> None:
        score = FakeScore(name="Scorer", score=0.5, metadata={"rationale": ""})
        evaluation = _score_to_evaluation(score)

        assert evaluation.reasoning == "Scorer: 0.5"


# ---------------------------------------------------------------------------
# AutoevalsAdapter.__call__
# ---------------------------------------------------------------------------


class TestAutoevalsAdapterCall:
    """Tests for the core adapter __call__ method."""

    @pytest.mark.asyncio
    async def test_output_from_evaluable(self) -> None:
        scorer = FakeScorer()
        adapter = AutoevalsAdapter(scorer, input_key=None)
        evaluable = Evaluable(eval_output="hello world")

        await adapter(evaluable)

        assert scorer.last_call_kwargs["output"] == "hello world"

    @pytest.mark.asyncio
    async def test_fixed_expected_passed_to_scorer(self) -> None:
        scorer = FakeScorer()
        adapter = AutoevalsAdapter(scorer, expected="ground truth", input_key=None)
        evaluable = Evaluable()

        await adapter(evaluable)

        assert scorer.last_call_kwargs["expected"] == "ground truth"

    @pytest.mark.asyncio
    async def test_expected_from_metadata(self) -> None:
        scorer = FakeScorer()
        adapter = AutoevalsAdapter(scorer, input_key=None)
        evaluable = Evaluable(eval_metadata={"expected": "from meta"})

        await adapter(evaluable)

        assert scorer.last_call_kwargs["expected"] == "from meta"

    @pytest.mark.asyncio
    async def test_expected_none_when_not_available(self) -> None:
        scorer = FakeScorer()
        adapter = AutoevalsAdapter(scorer, input_key=None)
        evaluable = Evaluable()

        await adapter(evaluable)

        assert scorer.last_call_kwargs["expected"] is None

    @pytest.mark.asyncio
    async def test_custom_expected_key(self) -> None:
        scorer = FakeScorer()
        adapter = AutoevalsAdapter(scorer, expected_key="reference", input_key=None)
        evaluable = Evaluable(eval_metadata={"reference": "ref value"})

        await adapter(evaluable)

        assert scorer.last_call_kwargs["expected"] == "ref value"

    @pytest.mark.asyncio
    async def test_input_key_default(self) -> None:
        scorer = FakeScorer()
        adapter = AutoevalsAdapter(scorer)
        evaluable = Evaluable(eval_input="my question")

        await adapter(evaluable)

        assert scorer.last_call_kwargs["input"] == "my question"

    @pytest.mark.asyncio
    async def test_input_key_custom(self) -> None:
        scorer = FakeScorer()
        adapter = AutoevalsAdapter(scorer, input_key="instructions")
        evaluable = Evaluable(eval_input="sort this")

        await adapter(evaluable)

        assert scorer.last_call_kwargs["instructions"] == "sort this"
        assert "input" not in scorer.last_call_kwargs

    @pytest.mark.asyncio
    async def test_input_key_none_skips_input(self) -> None:
        scorer = FakeScorer()
        adapter = AutoevalsAdapter(scorer, input_key=None)
        evaluable = Evaluable(eval_input="ignored")

        await adapter(evaluable)

        assert "input" not in scorer.last_call_kwargs

    @pytest.mark.asyncio
    async def test_extra_metadata_keys(self) -> None:
        scorer = FakeScorer()
        adapter = AutoevalsAdapter(
            scorer,
            input_key=None,
            extra_metadata_keys=("context", "criteria"),
        )
        evaluable = Evaluable(
            eval_metadata={
                "context": "some context",
                "criteria": "be concise",
                "other": "ignored",
            }
        )

        await adapter(evaluable)

        assert scorer.last_call_kwargs["context"] == "some context"
        assert scorer.last_call_kwargs["criteria"] == "be concise"
        assert "other" not in scorer.last_call_kwargs

    @pytest.mark.asyncio
    async def test_extra_metadata_keys_missing_silently_skipped(self) -> None:
        scorer = FakeScorer()
        adapter = AutoevalsAdapter(scorer, input_key=None, extra_metadata_keys=("context",))
        evaluable = Evaluable(eval_metadata={})

        await adapter(evaluable)

        assert "context" not in scorer.last_call_kwargs

    @pytest.mark.asyncio
    async def test_scorer_kwargs_forwarded(self) -> None:
        scorer = FakeScorer()
        adapter = AutoevalsAdapter(scorer, input_key=None, language="Spanish")
        evaluable = Evaluable()

        await adapter(evaluable)

        assert scorer.last_call_kwargs["language"] == "Spanish"

    @pytest.mark.asyncio
    async def test_returns_evaluation(self) -> None:
        score = FakeScore(name="Test", score=0.9, metadata={"rationale": "Good"})
        scorer = FakeScorer(return_score=score)
        adapter = AutoevalsAdapter(scorer, input_key=None)

        result = await adapter(Evaluable())

        assert isinstance(result, Evaluation)
        assert result.score == 0.9
        assert result.reasoning == "Good"

    @pytest.mark.asyncio
    async def test_scorer_exception_returns_zero_score(self) -> None:
        adapter = AutoevalsAdapter(RaisingScorer(), input_key=None)

        result = await adapter(Evaluable())

        assert result.score == 0.0
        assert "scorer exploded" in result.reasoning
        assert result.details["error"] == "ValueError"
        assert "traceback" in result.details

    @pytest.mark.asyncio
    async def test_fixed_expected_overrides_metadata(self) -> None:
        scorer = FakeScorer()
        adapter = AutoevalsAdapter(scorer, expected="fixed", input_key=None)
        evaluable = Evaluable(eval_metadata={"expected": "from meta"})

        await adapter(evaluable)

        assert scorer.last_call_kwargs["expected"] == "fixed"

    @pytest.mark.asyncio
    async def test_evaluable_expected_output_overrides_all(self) -> None:
        """evaluable.expected_output takes highest priority."""
        scorer = FakeScorer()
        adapter = AutoevalsAdapter(scorer, expected="fixed", input_key=None)
        evaluable = Evaluable(
            eval_metadata={"expected": "from meta"},
            expected_output="from-evaluable",
        )

        await adapter(evaluable)

        assert scorer.last_call_kwargs["expected"] == "from-evaluable"

    @pytest.mark.asyncio
    async def test_evaluable_expected_output_overrides_metadata(self) -> None:
        """evaluable.expected_output takes priority over metadata."""
        scorer = FakeScorer()
        adapter = AutoevalsAdapter(scorer, input_key=None)
        evaluable = Evaluable(
            eval_metadata={"expected": "from meta"},
            expected_output="from-evaluable",
        )

        await adapter(evaluable)

        assert scorer.last_call_kwargs["expected"] == "from-evaluable"

    @pytest.mark.asyncio
    async def test_unset_expected_output_falls_through(self) -> None:
        """When expected_output is UNSET, constructor/metadata still used."""
        scorer = FakeScorer()
        adapter = AutoevalsAdapter(scorer, expected="fixed", input_key=None)
        evaluable = Evaluable()  # expected_output defaults to UNSET

        await adapter(evaluable)

        assert scorer.last_call_kwargs["expected"] == "fixed"


# ---------------------------------------------------------------------------
# Pre-made evaluator factories
# ---------------------------------------------------------------------------


class TestLevenshteinMatch:
    """Tests for LevenshteinMatch factory."""

    def test_creates_adapter_with_correct_config(self) -> None:
        evaluator = LevenshteinMatch()
        assert isinstance(evaluator, AutoevalsAdapter)
        assert evaluator._input_key is None  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_passes_output_and_expected(self) -> None:
        with patch("pixie.evals.scorers._Levenshtein") as MockCls:
            mock_instance = MagicMock()
            mock_instance.eval_async = AsyncMock(
                return_value=FakeScore(name="Levenshtein", score=0.91)
            )
            MockCls.return_value = mock_instance

            evaluator = LevenshteinMatch()
            result = await evaluator(
                Evaluable(eval_output="hello wrld", expected_output="hello world"),
            )

            mock_instance.eval_async.assert_awaited_once()
            call_kwargs = mock_instance.eval_async.call_args
            assert call_kwargs.kwargs["output"] == "hello wrld"
            assert call_kwargs.kwargs["expected"] == "hello world"
            assert result.score == 0.91


class TestExactMatchEval:
    """Tests for ExactMatchEval factory."""

    def test_creates_adapter(self) -> None:
        evaluator = ExactMatchEval()
        assert isinstance(evaluator, AutoevalsAdapter)
        assert evaluator._input_key is None  # noqa: SLF001


class TestNumericDiffEval:
    """Tests for NumericDiffEval factory."""

    def test_creates_adapter(self) -> None:
        evaluator = NumericDiffEval()
        assert isinstance(evaluator, AutoevalsAdapter)
        assert evaluator._input_key is None  # noqa: SLF001


class TestJSONDiffEval:
    """Tests for JSONDiffEval factory."""

    def test_creates_adapter(self) -> None:
        evaluator = JSONDiffEval()
        assert isinstance(evaluator, AutoevalsAdapter)


class TestValidJSONEval:
    """Tests for ValidJSONEval factory."""

    def test_creates_adapter_without_expected(self) -> None:
        evaluator = ValidJSONEval()
        assert isinstance(evaluator, AutoevalsAdapter)


class TestListContainsEval:
    """Tests for ListContainsEval factory."""

    def test_creates_adapter(self) -> None:
        evaluator = ListContainsEval()
        assert isinstance(evaluator, AutoevalsAdapter)


class TestEmbeddingSimilarityEval:
    """Tests for EmbeddingSimilarityEval factory."""

    def test_creates_adapter(self) -> None:
        evaluator = EmbeddingSimilarityEval()
        assert isinstance(evaluator, AutoevalsAdapter)
        assert evaluator._input_key is None  # noqa: SLF001


class TestFactualityEval:
    """Tests for FactualityEval factory."""

    def test_creates_adapter_with_input_key(self) -> None:
        evaluator = FactualityEval()
        assert isinstance(evaluator, AutoevalsAdapter)
        assert evaluator._input_key == "input"  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_passes_input_from_evaluable(self) -> None:
        with patch("pixie.evals.scorers._Factuality") as MockCls:
            mock_instance = MagicMock()
            mock_instance.eval_async = AsyncMock(
                return_value=FakeScore(
                    name="Factuality",
                    score=1.0,
                    metadata={"rationale": "Correct facts"},
                )
            )
            MockCls.return_value = mock_instance

            evaluator = FactualityEval()
            result = await evaluator(
                Evaluable(
                    eval_input="Q?",
                    eval_output="Paris is the capital",
                    expected_output="Paris is the capital",
                ),
            )

            call_kwargs = mock_instance.eval_async.call_args.kwargs
            assert call_kwargs["input"] == "Q?"
            assert call_kwargs["output"] == "Paris is the capital"
            assert call_kwargs["expected"] == "Paris is the capital"
            assert result.score == 1.0
            assert result.reasoning == "Correct facts"


class TestClosedQAEval:
    """Tests for ClosedQAEval factory."""

    def test_creates_adapter_with_criteria_metadata(self) -> None:
        evaluator = ClosedQAEval()
        assert isinstance(evaluator, AutoevalsAdapter)
        assert "criteria" in evaluator._extra_metadata_keys  # noqa: SLF001


class TestBattleEval:
    """Tests for BattleEval factory."""

    def test_maps_input_to_instructions(self) -> None:
        evaluator = BattleEval()
        assert evaluator._input_key == "instructions"  # noqa: SLF001


class TestHumorEval:
    """Tests for HumorEval factory."""

    def test_no_expected_no_input(self) -> None:
        evaluator = HumorEval()
        assert evaluator._input_key is None  # noqa: SLF001


class TestSecurityEval:
    """Tests for SecurityEval factory."""

    def test_maps_input_to_instructions(self) -> None:
        evaluator = SecurityEval()
        assert evaluator._input_key == "instructions"  # noqa: SLF001


class TestSqlEval:
    """Tests for SqlEval factory."""

    def test_creates_adapter(self) -> None:
        evaluator = SqlEval()
        assert isinstance(evaluator, AutoevalsAdapter)


class TestSummaryEval:
    """Tests for SummaryEval factory."""

    def test_creates_adapter(self) -> None:
        evaluator = SummaryEval()
        assert isinstance(evaluator, AutoevalsAdapter)


class TestTranslationEval:
    """Tests for TranslationEval factory."""

    def test_passes_language_kwarg(self) -> None:
        evaluator = TranslationEval(language="Spanish")
        assert evaluator._scorer_kwargs.get("language") == "Spanish"  # noqa: SLF001


class TestPossibleEval:
    """Tests for PossibleEval factory."""

    def test_creates_adapter(self) -> None:
        evaluator = PossibleEval()
        assert isinstance(evaluator, AutoevalsAdapter)


class TestModerationEval:
    """Tests for ModerationEval factory."""

    def test_creates_adapter_no_input(self) -> None:
        evaluator = ModerationEval()
        assert isinstance(evaluator, AutoevalsAdapter)
        assert evaluator._input_key is None  # noqa: SLF001


class TestContextRelevancyEval:
    """Tests for ContextRelevancyEval factory."""

    def test_has_context_metadata_key(self) -> None:
        evaluator = ContextRelevancyEval()
        assert "context" in evaluator._extra_metadata_keys  # noqa: SLF001


class TestFaithfulnessEval:
    """Tests for FaithfulnessEval factory."""

    def test_has_context_metadata_key(self) -> None:
        evaluator = FaithfulnessEval()
        assert "context" in evaluator._extra_metadata_keys  # noqa: SLF001


class TestAnswerRelevancyEval:
    """Tests for AnswerRelevancyEval factory."""

    def test_has_context_metadata_key(self) -> None:
        evaluator = AnswerRelevancyEval()
        assert "context" in evaluator._extra_metadata_keys  # noqa: SLF001


class TestAnswerCorrectnessEval:
    """Tests for AnswerCorrectnessEval factory."""

    def test_has_context_metadata_key(self) -> None:
        evaluator = AnswerCorrectnessEval()
        assert "context" in evaluator._extra_metadata_keys  # noqa: SLF001
