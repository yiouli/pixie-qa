"""pixie.evals — evaluation harness for LLM applications.

Public API:
    - ``Evaluation`` — result dataclass for a single evaluator run
    - ``Evaluator`` — protocol for evaluation callables
    - ``evaluate`` — run one evaluator against one evaluable
    - ``run_and_evaluate`` — evaluate spans from a MemoryTraceHandler
    - ``assert_pass`` — batch evaluation with pass/fail criteria
    - ``assert_dataset_pass`` — load a dataset and run assert_pass
    - ``EvalAssertionError`` — raised when assert_pass fails
    - ``capture_traces`` — context manager for in-memory trace capture
    - ``MemoryTraceHandler`` — InstrumentationHandler that collects spans
    - ``ScoreThreshold`` — configurable pass criteria
    - ``last_llm_call`` / ``root`` — trace-to-evaluable helpers

Pre-made evaluators (autoevals adapters):
    - ``AutoevalsAdapter`` — generic wrapper for any autoevals ``Scorer``
    - ``LevenshteinMatch`` — edit-distance string similarity
    - ``ExactMatchEval`` — exact value comparison
    - ``NumericDiffEval`` — normalised numeric difference
    - ``JSONDiffEval`` — structural JSON comparison
    - ``ValidJSONEval`` — JSON syntax / schema validation
    - ``ListContainsEval`` — list overlap
    - ``EmbeddingSimilarityEval`` — embedding cosine similarity
    - ``FactualityEval`` — LLM factual accuracy check
    - ``ClosedQAEval`` — closed-book QA evaluation
    - ``BattleEval`` — head-to-head comparison
    - ``HumorEval`` — humor detection
    - ``SecurityEval`` — security vulnerability check
    - ``SqlEval`` — SQL equivalence
    - ``SummaryEval`` — summarisation quality
    - ``TranslationEval`` — translation quality
    - ``PossibleEval`` — feasibility check
    - ``ModerationEval`` — content moderation
    - ``ContextRelevancyEval`` — RAGAS context relevancy
    - ``FaithfulnessEval`` — RAGAS faithfulness
    - ``AnswerRelevancyEval`` — RAGAS answer relevancy
    - ``AnswerCorrectnessEval`` — RAGAS answer correctness
"""

from pixie.evals.criteria import ScoreThreshold
from pixie.evals.eval_utils import (
    EvalAssertionError,
    assert_dataset_pass,
    assert_pass,
    run_and_evaluate,
)
from pixie.evals.evaluation import Evaluation, Evaluator, evaluate
from pixie.evals.scorecard import (
    ScorecardCollector,
    ScorecardReport,
    generate_scorecard_html,
    save_scorecard,
)
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
)
from pixie.evals.trace_capture import MemoryTraceHandler, capture_traces
from pixie.evals.trace_helpers import last_llm_call, root

__all__ = [
    "AnswerCorrectnessEval",
    "AnswerRelevancyEval",
    "AutoevalsAdapter",
    "BattleEval",
    "ClosedQAEval",
    "ContextRelevancyEval",
    "EmbeddingSimilarityEval",
    "EvalAssertionError",
    "Evaluation",
    "Evaluator",
    "ExactMatchEval",
    "FactualityEval",
    "FaithfulnessEval",
    "HumorEval",
    "JSONDiffEval",
    "LevenshteinMatch",
    "ListContainsEval",
    "MemoryTraceHandler",
    "ModerationEval",
    "NumericDiffEval",
    "PossibleEval",
    "ScoreThreshold",
    "ScorecardCollector",
    "ScorecardReport",
    "SecurityEval",
    "SqlEval",
    "SummaryEval",
    "TranslationEval",
    "ValidJSONEval",
    "assert_dataset_pass",
    "assert_pass",
    "capture_traces",
    "evaluate",
    "generate_scorecard_html",
    "last_llm_call",
    "root",
    "run_and_evaluate",
    "save_scorecard",
]
