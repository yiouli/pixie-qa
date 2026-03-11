"""Autoevals adapters — pre-made evaluators wrapping ``autoevals`` scorers.

This module provides :class:`AutoevalsAdapter`, which bridges the
autoevals ``Scorer`` interface to pixie's ``Evaluator`` protocol, and
a set of factory functions for common evaluation tasks.

Public API (all are also re-exported from ``pixie.evals``):

**Core adapter:**
    - :class:`AutoevalsAdapter` — generic wrapper for any autoevals ``Scorer``.

**Heuristic scorers (no LLM required):**
    - :func:`LevenshteinMatch` — edit-distance string similarity.
    - :func:`ExactMatchEval` — exact value comparison.
    - :func:`NumericDiffEval` — normalised numeric difference.
    - :func:`JSONDiffEval` — structural JSON comparison.
    - :func:`ValidJSONEval` — JSON syntax / schema validation.
    - :func:`ListContainsEval` — overlap between two string lists.

**Embedding scorer:**
    - :func:`EmbeddingSimilarityEval` — cosine similarity via embeddings.

**LLM-as-judge scorers:**
    - :func:`FactualityEval`, :func:`ClosedQAEval`, :func:`BattleEval`,
      :func:`HumorEval`, :func:`SecurityEval`, :func:`SqlEval`,
      :func:`SummaryEval`, :func:`TranslationEval`, :func:`PossibleEval`.

**Moderation:**
    - :func:`ModerationEval` — OpenAI content-moderation check.

**RAGAS metrics:**
    - :func:`ContextRelevancyEval`, :func:`FaithfulnessEval`,
      :func:`AnswerRelevancyEval`, :func:`AnswerCorrectnessEval`.
"""

from __future__ import annotations

import traceback as _tb
from typing import Any

from autoevals.json import JSONDiff as _JSONDiff
from autoevals.json import ValidJSON as _ValidJSON
from autoevals.list import ListContains as _ListContains
from autoevals.llm import (
    Battle as _Battle,
)
from autoevals.llm import (
    ClosedQA as _ClosedQA,
)
from autoevals.llm import (
    Factuality as _Factuality,
)
from autoevals.llm import (
    Humor as _Humor,
)
from autoevals.llm import (
    Possible as _Possible,
)
from autoevals.llm import (
    Security as _Security,
)
from autoevals.llm import (
    Sql as _Sql,
)
from autoevals.llm import (
    Summary as _Summary,
)
from autoevals.llm import (
    Translation as _Translation,
)
from autoevals.moderation import Moderation as _Moderation
from autoevals.number import NumericDiff as _NumericDiff
from autoevals.ragas import (
    AnswerCorrectness as _AnswerCorrectness,
)
from autoevals.ragas import (
    AnswerRelevancy as _AnswerRelevancy,
)
from autoevals.ragas import (
    ContextRelevancy as _ContextRelevancy,
)
from autoevals.ragas import (
    Faithfulness as _Faithfulness,
)
from autoevals.score import Score as _Score
from autoevals.score import Scorer as _Scorer
from autoevals.string import EmbeddingSimilarity as _EmbeddingSimilarity
from autoevals.string import Levenshtein as _Levenshtein
from autoevals.value import ExactMatch as _ExactMatch

from pixie.evals.evaluation import Evaluation
from pixie.storage.evaluable import Evaluable
from pixie.storage.tree import ObservationNode

# Sentinel used to distinguish "caller did not pass expected" from ``None``.
_UNSET: Any = object()


# ---------------------------------------------------------------------------
# Score → Evaluation conversion
# ---------------------------------------------------------------------------


def _score_to_evaluation(score: _Score) -> Evaluation:
    """Convert an autoevals ``Score`` to a pixie ``Evaluation``.

    Mapping rules:
        - ``score.score``  → ``evaluation.score`` (``None`` becomes ``0.0``).
        - ``score.metadata["rationale"]`` → ``evaluation.reasoning`` when
          present and non-empty; otherwise a default string is generated.
        - The full ``score.metadata`` dict is forwarded to
          ``evaluation.details`` with an extra ``scorer_name`` key.
    """
    numeric = float(score.score) if score.score is not None else 0.0
    metadata: dict[str, Any] = dict(score.metadata) if score.metadata else {}
    metadata["scorer_name"] = score.name

    rationale = metadata.get("rationale")
    if rationale and isinstance(rationale, str) and rationale.strip():
        reasoning = rationale
    elif score.score is None:
        reasoning = "Evaluation skipped (score is None)"
    else:
        reasoning = f"{score.name}: {score.score}"

    return Evaluation(score=numeric, reasoning=reasoning, details=metadata)


# ---------------------------------------------------------------------------
# Core adapter
# ---------------------------------------------------------------------------


class AutoevalsAdapter:
    """Wrap an autoevals ``Scorer`` to satisfy the pixie ``Evaluator`` protocol.

    The adapter translates between two interfaces:

    * **pixie** — evaluator receives :class:`~pixie.storage.evaluable.Evaluable`
      (``eval_input``, ``eval_output``, ``eval_metadata``) and returns
      :class:`~pixie.evals.evaluation.Evaluation`.
    * **autoevals** — scorer receives ``output``, ``expected``, ``**kwargs``
      and returns :class:`autoevals.score.Score`.

    Args:
        scorer: The autoevals ``Scorer`` instance to delegate to.
        expected: Fixed expected value. If not provided, the adapter reads
            ``evaluable.eval_metadata[expected_key]`` at call time.
        expected_key: Metadata key to read ``expected`` from (default
            ``"expected"``).
        input_key: If not ``None``, ``evaluable.eval_input`` is forwarded as
            this kwarg to the scorer (default ``"input"``). Set to ``None``
            to skip.
        extra_metadata_keys: Additional metadata keys to forward as kwargs.
        **scorer_kwargs: Extra fixed kwargs passed to every ``eval_async``
            call.
    """

    def __init__(
        self,
        scorer: _Scorer,
        *,
        expected: Any = _UNSET,
        expected_key: str = "expected",
        input_key: str | None = "input",
        extra_metadata_keys: tuple[str, ...] = (),
        **scorer_kwargs: Any,
    ) -> None:
        self._scorer = scorer
        self._expected = expected
        self._expected_key = expected_key
        self._input_key = input_key
        self._extra_metadata_keys = extra_metadata_keys
        self._scorer_kwargs = scorer_kwargs

    async def __call__(
        self,
        evaluable: Evaluable,
        *,
        expected_output: Any = None,
        trace: list[ObservationNode] | None = None,
    ) -> Evaluation:
        """Run the wrapped scorer and return a pixie ``Evaluation``.

        Expected-value resolution priority (highest to lowest):
            1. *expected_output* passed at call time (from ``evaluate()``).
            2. Constructor-provided ``expected``.
            3. ``evaluable.eval_metadata[expected_key]``.
        """
        try:
            output = evaluable.eval_output

            # Resolve expected — call-time > constructor > metadata
            if expected_output is not None:
                expected = expected_output
            elif self._expected is not _UNSET:
                expected = self._expected
            else:
                expected = evaluable.eval_metadata.get(self._expected_key)

            # Build kwargs
            kwargs: dict[str, Any] = {}
            if self._input_key is not None:
                kwargs[self._input_key] = evaluable.eval_input
            for key in self._extra_metadata_keys:
                if key in evaluable.eval_metadata:
                    kwargs[key] = evaluable.eval_metadata[key]
            kwargs.update(self._scorer_kwargs)

            score = await self._scorer.eval_async(
                output=output, expected=expected, **kwargs
            )
            return _score_to_evaluation(score)
        except Exception as exc:
            tb = _tb.format_exc()
            return Evaluation(
                score=0.0,
                reasoning=str(exc),
                details={"error": type(exc).__name__, "traceback": tb},
            )


# ---------------------------------------------------------------------------
# Pre-made evaluator factories — Heuristic
# ---------------------------------------------------------------------------


def LevenshteinMatch() -> AutoevalsAdapter:  # noqa: N802
    """Edit-distance string similarity evaluator.

    Wraps :class:`autoevals.string.Levenshtein`.  Pass ``expected_output``
    via :func:`~pixie.evals.eval_utils.assert_pass` or at call time.
    """
    return AutoevalsAdapter(
        _Levenshtein(),
        input_key=None,
    )


def ExactMatchEval() -> AutoevalsAdapter:  # noqa: N802
    """Exact value comparison evaluator.

    Wraps :class:`autoevals.value.ExactMatch`.  Pass ``expected_output``
    via :func:`~pixie.evals.eval_utils.assert_pass` or at call time.
    """
    return AutoevalsAdapter(
        _ExactMatch(),
        input_key=None,
    )


def NumericDiffEval() -> AutoevalsAdapter:  # noqa: N802
    """Normalised numeric difference evaluator.

    Wraps :class:`autoevals.number.NumericDiff`.  Pass ``expected_output``
    via :func:`~pixie.evals.eval_utils.assert_pass` or at call time.
    """
    return AutoevalsAdapter(
        _NumericDiff(),
        input_key=None,
    )


def JSONDiffEval(  # noqa: N802
    *,
    string_scorer: Any = None,
) -> AutoevalsAdapter:
    """Structural JSON comparison evaluator.

    Wraps :class:`autoevals.json.JSONDiff`.  Pass ``expected_output``
    via :func:`~pixie.evals.eval_utils.assert_pass` or at call time.

    Args:
        string_scorer: Optional pairwise scorer for string fields.
    """
    scorer_kwargs: dict[str, Any] = {}
    if string_scorer is not None:
        scorer_kwargs["string_scorer"] = string_scorer
    return AutoevalsAdapter(
        _JSONDiff(**scorer_kwargs),
        input_key=None,
    )


def ValidJSONEval(  # noqa: N802
    *,
    schema: Any = None,
) -> AutoevalsAdapter:
    """JSON syntax / schema validation evaluator.

    Wraps :class:`autoevals.json.ValidJSON`.

    Args:
        schema: Optional JSON Schema to validate against.
    """
    scorer_kwargs: dict[str, Any] = {}
    if schema is not None:
        scorer_kwargs["schema"] = schema
    return AutoevalsAdapter(
        _ValidJSON(**scorer_kwargs),
        input_key=None,
    )


def ListContainsEval(  # noqa: N802
    *,
    pairwise_scorer: Any = None,
    allow_extra_entities: bool = False,
) -> AutoevalsAdapter:
    """List overlap evaluator.

    Wraps :class:`autoevals.list.ListContains`.  Pass ``expected_output``
    via :func:`~pixie.evals.eval_utils.assert_pass` or at call time.

    Args:
        pairwise_scorer: Optional scorer for pairwise element comparison.
        allow_extra_entities: If True, extra items in output are not penalised.
    """
    scorer_kwargs: dict[str, Any] = {}
    if pairwise_scorer is not None:
        scorer_kwargs["pairwise_scorer"] = pairwise_scorer
    scorer_kwargs["allow_extra_entities"] = allow_extra_entities
    return AutoevalsAdapter(
        _ListContains(**scorer_kwargs),
        input_key=None,
    )


# ---------------------------------------------------------------------------
# Pre-made evaluator factories — Embedding
# ---------------------------------------------------------------------------


def EmbeddingSimilarityEval(  # noqa: N802
    *,
    prefix: str | None = None,
    model: str | None = None,
    client: Any = None,
) -> AutoevalsAdapter:
    """Embedding-based string similarity evaluator.

    Wraps :class:`autoevals.string.EmbeddingSimilarity`.  Pass
    ``expected_output`` via :func:`~pixie.evals.eval_utils.assert_pass`
    or at call time.

    Args:
        prefix: Optional text to prepend for domain context.
        model: Embedding model name.
        client: OpenAI client instance.
    """
    scorer_kwargs: dict[str, Any] = {}
    if prefix is not None:
        scorer_kwargs["prefix"] = prefix
    if model is not None:
        scorer_kwargs["model"] = model
    if client is not None:
        scorer_kwargs["client"] = client
    return AutoevalsAdapter(
        _EmbeddingSimilarity(**scorer_kwargs),
        input_key=None,
    )


# ---------------------------------------------------------------------------
# Pre-made evaluator factories — LLM-as-judge
# ---------------------------------------------------------------------------


def FactualityEval(  # noqa: N802
    *,
    model: str | None = None,
    client: Any = None,
) -> AutoevalsAdapter:
    """Factual accuracy evaluator.

    Wraps :class:`autoevals.llm.Factuality`.  The evaluable's
    ``eval_input`` is forwarded as the ``input`` kwarg.  Pass
    ``expected_output`` via :func:`~pixie.evals.eval_utils.assert_pass`
    or at call time.

    Args:
        model: LLM model name.
        client: OpenAI client instance.
    """
    scorer_kwargs: dict[str, Any] = {}
    if model is not None:
        scorer_kwargs["model"] = model
    if client is not None:
        scorer_kwargs["client"] = client
    return AutoevalsAdapter(
        _Factuality(**scorer_kwargs),
        input_key="input",
    )


def ClosedQAEval(  # noqa: N802
    *,
    model: str | None = None,
    client: Any = None,
) -> AutoevalsAdapter:
    """Closed-book question-answering evaluator.

    Wraps :class:`autoevals.llm.ClosedQA`.  Forwards ``eval_input`` as
    ``input`` and ``eval_metadata["criteria"]`` when present.  Pass
    ``expected_output`` via :func:`~pixie.evals.eval_utils.assert_pass`
    or at call time.

    Args:
        model: LLM model name.
        client: OpenAI client instance.
    """
    scorer_kwargs: dict[str, Any] = {}
    if model is not None:
        scorer_kwargs["model"] = model
    if client is not None:
        scorer_kwargs["client"] = client
    return AutoevalsAdapter(
        _ClosedQA(**scorer_kwargs),
        input_key="input",
        extra_metadata_keys=("criteria",),
    )


def BattleEval(  # noqa: N802
    *,
    model: str | None = None,
    client: Any = None,
) -> AutoevalsAdapter:
    """Head-to-head comparison evaluator.

    Wraps :class:`autoevals.llm.Battle`.  The evaluable's ``eval_input``
    is forwarded as the ``instructions`` kwarg.  Pass ``expected_output``
    via :func:`~pixie.evals.eval_utils.assert_pass` or at call time.

    Args:
        model: LLM model name.
        client: OpenAI client instance.
    """
    scorer_kwargs: dict[str, Any] = {}
    if model is not None:
        scorer_kwargs["model"] = model
    if client is not None:
        scorer_kwargs["client"] = client
    return AutoevalsAdapter(
        _Battle(**scorer_kwargs),
        input_key="instructions",
    )


def HumorEval(  # noqa: N802
    *,
    model: str | None = None,
    client: Any = None,
) -> AutoevalsAdapter:
    """Humor detection evaluator.

    Wraps :class:`autoevals.llm.Humor`.

    Args:
        model: LLM model name.
        client: OpenAI client instance.
    """
    scorer_kwargs: dict[str, Any] = {}
    if model is not None:
        scorer_kwargs["model"] = model
    if client is not None:
        scorer_kwargs["client"] = client
    return AutoevalsAdapter(
        _Humor(**scorer_kwargs),
        input_key=None,
    )


def SecurityEval(  # noqa: N802
    *,
    model: str | None = None,
    client: Any = None,
) -> AutoevalsAdapter:
    """Security vulnerability evaluator.

    Wraps :class:`autoevals.llm.Security`.  The evaluable's ``eval_input``
    is forwarded as the ``instructions`` kwarg.

    Args:
        model: LLM model name.
        client: OpenAI client instance.
    """
    scorer_kwargs: dict[str, Any] = {}
    if model is not None:
        scorer_kwargs["model"] = model
    if client is not None:
        scorer_kwargs["client"] = client
    return AutoevalsAdapter(
        _Security(**scorer_kwargs),
        input_key="instructions",
    )


def SqlEval(  # noqa: N802
    *,
    model: str | None = None,
    client: Any = None,
) -> AutoevalsAdapter:
    """SQL equivalence evaluator.

    Wraps :class:`autoevals.llm.Sql`.  Pass ``expected_output``
    via :func:`~pixie.evals.eval_utils.assert_pass` or at call time.

    Args:
        model: LLM model name.
        client: OpenAI client instance.
    """
    scorer_kwargs: dict[str, Any] = {}
    if model is not None:
        scorer_kwargs["model"] = model
    if client is not None:
        scorer_kwargs["client"] = client
    return AutoevalsAdapter(
        _Sql(**scorer_kwargs),
        input_key="input",
    )


def SummaryEval(  # noqa: N802
    *,
    model: str | None = None,
    client: Any = None,
) -> AutoevalsAdapter:
    """Summarisation quality evaluator.

    Wraps :class:`autoevals.llm.Summary`.  Pass ``expected_output``
    via :func:`~pixie.evals.eval_utils.assert_pass` or at call time.

    Args:
        model: LLM model name.
        client: OpenAI client instance.
    """
    scorer_kwargs: dict[str, Any] = {}
    if model is not None:
        scorer_kwargs["model"] = model
    if client is not None:
        scorer_kwargs["client"] = client
    return AutoevalsAdapter(
        _Summary(**scorer_kwargs),
        input_key="input",
    )


def TranslationEval(  # noqa: N802
    *,
    language: str | None = None,
    model: str | None = None,
    client: Any = None,
) -> AutoevalsAdapter:
    """Translation quality evaluator.

    Wraps :class:`autoevals.llm.Translation`.  The ``language`` kwarg is
    forwarded to every scorer call.  Pass ``expected_output`` via
    :func:`~pixie.evals.eval_utils.assert_pass` or at call time.

    Args:
        language: Target language (e.g. ``"Spanish"``).
        model: LLM model name.
        client: OpenAI client instance.
    """
    ctor_kwargs: dict[str, Any] = {}
    if model is not None:
        ctor_kwargs["model"] = model
    if client is not None:
        ctor_kwargs["client"] = client
    extra: dict[str, Any] = {}
    if language is not None:
        extra["language"] = language
    return AutoevalsAdapter(
        _Translation(**ctor_kwargs),
        input_key="input",
        **extra,
    )


def PossibleEval(  # noqa: N802
    *,
    model: str | None = None,
    client: Any = None,
) -> AutoevalsAdapter:
    """Feasibility evaluator.

    Wraps :class:`autoevals.llm.Possible`.

    Args:
        model: LLM model name.
        client: OpenAI client instance.
    """
    scorer_kwargs: dict[str, Any] = {}
    if model is not None:
        scorer_kwargs["model"] = model
    if client is not None:
        scorer_kwargs["client"] = client
    return AutoevalsAdapter(
        _Possible(**scorer_kwargs),
        input_key="input",
    )


# ---------------------------------------------------------------------------
# Pre-made evaluator factories — Moderation
# ---------------------------------------------------------------------------


def ModerationEval(  # noqa: N802
    *,
    threshold: float | None = None,
    client: Any = None,
) -> AutoevalsAdapter:
    """Content-moderation evaluator.

    Wraps :class:`autoevals.moderation.Moderation`.

    Args:
        threshold: Custom flagging threshold.
        client: OpenAI client instance.
    """
    scorer_kwargs: dict[str, Any] = {}
    if threshold is not None:
        scorer_kwargs["threshold"] = threshold
    if client is not None:
        scorer_kwargs["client"] = client
    return AutoevalsAdapter(
        _Moderation(**scorer_kwargs),
        input_key=None,
    )


# ---------------------------------------------------------------------------
# Pre-made evaluator factories — RAGAS
# ---------------------------------------------------------------------------


def ContextRelevancyEval(  # noqa: N802
    *,
    client: Any = None,
) -> AutoevalsAdapter:
    """Context relevancy evaluator (RAGAS).

    Wraps :class:`autoevals.ragas.ContextRelevancy`.  Pass
    ``expected_output`` via :func:`~pixie.evals.eval_utils.assert_pass`
    or at call time.

    Args:
        client: OpenAI client instance.
    """
    scorer_kwargs: dict[str, Any] = {}
    if client is not None:
        scorer_kwargs["client"] = client
    return AutoevalsAdapter(
        _ContextRelevancy(**scorer_kwargs),
        input_key="input",
        extra_metadata_keys=("context",),
    )


def FaithfulnessEval(  # noqa: N802
    *,
    client: Any = None,
) -> AutoevalsAdapter:
    """Faithfulness evaluator (RAGAS).

    Wraps :class:`autoevals.ragas.Faithfulness`.

    Args:
        client: OpenAI client instance.
    """
    scorer_kwargs: dict[str, Any] = {}
    if client is not None:
        scorer_kwargs["client"] = client
    return AutoevalsAdapter(
        _Faithfulness(**scorer_kwargs),
        input_key="input",
        extra_metadata_keys=("context",),
    )


def AnswerRelevancyEval(  # noqa: N802
    *,
    client: Any = None,
) -> AutoevalsAdapter:
    """Answer relevancy evaluator (RAGAS).

    Wraps :class:`autoevals.ragas.AnswerRelevancy`.

    Args:
        client: OpenAI client instance.
    """
    scorer_kwargs: dict[str, Any] = {}
    if client is not None:
        scorer_kwargs["client"] = client
    return AutoevalsAdapter(
        _AnswerRelevancy(**scorer_kwargs),
        input_key="input",
        extra_metadata_keys=("context",),
    )


def AnswerCorrectnessEval(  # noqa: N802
    *,
    client: Any = None,
) -> AutoevalsAdapter:
    """Answer correctness evaluator (RAGAS).

    Wraps :class:`autoevals.ragas.AnswerCorrectness`.  Pass
    ``expected_output`` via :func:`~pixie.evals.eval_utils.assert_pass`
    or at call time.

    Args:
        client: OpenAI client instance.
    """
    scorer_kwargs: dict[str, Any] = {}
    if client is not None:
        scorer_kwargs["client"] = client
    return AutoevalsAdapter(
        _AnswerCorrectness(**scorer_kwargs),
        input_key="input",
        extra_metadata_keys=("context",),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "AutoevalsAdapter",
    "AnswerCorrectnessEval",
    "AnswerRelevancyEval",
    "BattleEval",
    "ClosedQAEval",
    "ContextRelevancyEval",
    "EmbeddingSimilarityEval",
    "ExactMatchEval",
    "FactualityEval",
    "FaithfulnessEval",
    "HumorEval",
    "JSONDiffEval",
    "LevenshteinMatch",
    "ListContainsEval",
    "ModerationEval",
    "NumericDiffEval",
    "PossibleEval",
    "SecurityEval",
    "SqlEval",
    "SummaryEval",
    "TranslationEval",
    "ValidJSONEval",
    "_score_to_evaluation",
]
