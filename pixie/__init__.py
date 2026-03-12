"""pixie — automated quality assurance for AI applications.

Re-exports the full public API so users can ``from pixie import ...``
for every commonly used symbol without needing submodule paths.
"""

# -- Instrumentation ----------------------------------------------------------
# -- Dataset / Storage --------------------------------------------------------
from pixie.dataset.store import DatasetStore

# -- Evals --------------------------------------------------------------------
from pixie.evals.criteria import ScoreThreshold
from pixie.evals.eval_utils import (
    EvalAssertionError,
    assert_dataset_pass,
    assert_pass,
    run_and_evaluate,
)
from pixie.evals.evaluation import Evaluation, Evaluator, evaluate
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
from pixie.instrumentation.handlers import StorageHandler, enable_storage
from pixie.instrumentation.observation import (
    add_handler,
    flush,
    init,
    observe,
    remove_handler,
    start_observation,
)
from pixie.storage.evaluable import UNSET, Evaluable
from pixie.storage.store import ObservationStore

__all__ = [
    # Instrumentation
    "StorageHandler",
    "add_handler",
    "enable_storage",
    "flush",
    "init",
    "observe",
    "remove_handler",
    "start_observation",
    # Evals
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
    "SecurityEval",
    "SqlEval",
    "SummaryEval",
    "TranslationEval",
    "ValidJSONEval",
    "assert_dataset_pass",
    "assert_pass",
    "capture_traces",
    "evaluate",
    "last_llm_call",
    "root",
    "run_and_evaluate",
    # Dataset / Storage
    "DatasetStore",
    "Evaluable",
    "ObservationStore",
    "UNSET",
]
