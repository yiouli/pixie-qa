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
    enable_llm_tracing,
    flush,
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
    clear_eval_input,
    clear_eval_output,
    get_eval_input,
    get_eval_output,
    init_eval_output,
    set_eval_input,
)
from pixie.storage.evaluable import UNSET, Evaluable, NamedData, TestCase

__all__ = [
    # Instrumentation
    "WrapRegistryMissError",
    "WrapTypeMismatchError",
    "WrapLogEntry",
    "WrappedData",
    "add_handler",
    "clear_eval_input",
    "clear_eval_output",
    "flush",
    "filter_by_purpose",
    "get_eval_input",
    "get_eval_output",
    "enable_llm_tracing",
    "init_eval_output",
    "load_wrap_log_entries",
    "parse_wrapped_data_list",
    "remove_handler",
    "set_eval_input",
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
