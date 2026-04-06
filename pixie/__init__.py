"""pixie — automated quality assurance for AI applications.

Re-exports the full public API so users can ``from pixie import ...``
for every commonly used symbol without needing submodule paths.
"""

from pixie.evals.criteria import ScoreThreshold
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

# -- Instrumentation ----------------------------------------------------------
from pixie.instrumentation.observation import (
    add_handler,
    flush,
    init,
    remove_handler,
)
from pixie.instrumentation.wrap import (
    WrapRegistryMissError,
    WrapTypeMismatchError,
    wrap,
)
from pixie.instrumentation.wrap_log import (
    WrapLogEntry,
    WrappedData,
    filter_by_purpose,
    load_wrap_log_entries,
    parse_wrapped_data_list,
)
from pixie.instrumentation.wrap_registry import (
    clear_capture_registry,
    clear_input_registry,
    get_capture_registry,
    get_input_registry,
    get_output_capture_registry,
    get_state_capture_registry,
    init_capture_registry,
    set_input_registry,
)
from pixie.storage.evaluable import UNSET, Evaluable, NamedData, TestCase

__all__ = [
    # Instrumentation
    "WrapRegistryMissError",
    "WrapTypeMismatchError",
    "WrapLogEntry",
    "WrappedData",
    "add_handler",
    "clear_capture_registry",
    "clear_input_registry",
    "flush",
    "filter_by_purpose",
    "get_capture_registry",
    "get_input_registry",
    "get_output_capture_registry",
    "get_state_capture_registry",
    "init",
    "init_capture_registry",
    "load_wrap_log_entries",
    "parse_wrapped_data_list",
    "remove_handler",
    "set_input_registry",
    "wrap",
    # Evals
    "AnswerCorrectness",
    "AnswerRelevancy",
    "AutoevalsAdapter",
    "Battle",
    "ClosedQA",
    "ContextRelevancy",
    "EmbeddingSimilarity",
    "Evaluation",
    "Evaluator",
    "ExactMatch",
    "Factuality",
    "Faithfulness",
    "Humor",
    "JSONDiff",
    "LevenshteinMatch",
    "ListContains",
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
    "configure_rate_limits",
    "create_llm_evaluator",
    "evaluate",
    # Dataset / Storage
    "Evaluable",
    "NamedData",
    "TestCase",
    "UNSET",
]
