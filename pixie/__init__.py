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
from pixie.evals.llm_evaluator import create_llm_evaluator
from pixie.evals.rate_limiter import RateLimitConfig, configure_rate_limits
from pixie.evals.scorers import (
    AnswerCorrectness,
    AnswerRelevancy,
    AutoevalsAdapter,
    Battle,
    ClosedQA,
    ContextRelevancy,
    EmbeddingSimilarity,
    ExactMatch,
    Factuality,
    Faithfulness,
    Humor,
    JSONDiff,
    LevenshteinMatch,
    ListContains,
    Moderation,
    NumericDiff,
    Possible,
    Security,
    Sql,
    Summary,
    Translation,
    ValidJSON,
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
    "AnswerCorrectness",
    "AnswerRelevancy",
    "AutoevalsAdapter",
    "Battle",
    "ClosedQA",
    "ContextRelevancy",
    "EmbeddingSimilarity",
    "EvalAssertionError",
    "Evaluation",
    "Evaluator",
    "ExactMatch",
    "Factuality",
    "Faithfulness",
    "Humor",
    "JSONDiff",
    "LevenshteinMatch",
    "ListContains",
    "MemoryTraceHandler",
    "Moderation",
    "NumericDiff",
    "Possible",
    "RateLimitConfig",
    "ScoreThreshold",
    "Security",
    "Sql",
    "Summary",
    "Translation",
    "ValidJSON",
    "assert_dataset_pass",
    "assert_pass",
    "capture_traces",
    "configure_rate_limits",
    "create_llm_evaluator",
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
