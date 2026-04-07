"""pixie — automated quality assurance for AI applications.

Re-exports the full public API so users can ``from pixie import ...``
for every commonly used symbol without needing submodule paths.
"""

from pixie.eval.evaluable import UNSET, Evaluable, NamedData, TestCase
from pixie.eval.evaluation import Evaluation, Evaluator, evaluate
from pixie.eval.llm_evaluator import create_llm_evaluator
from pixie.eval.rate_limiter import RateLimitConfig, configure_rate_limits
from pixie.eval.scorers import (
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
from pixie.instrumentation.llm_tracing import (
    add_handler,
    enable_llm_tracing,
    flush,
    remove_handler,
)
from pixie.instrumentation.wrap import (
    WrapLogEntry,
    WrappedData,
    WrapRegistryMissError,
    WrapTypeMismatchError,
    clear_eval_input,
    clear_eval_output,
    filter_by_purpose,
    get_eval_input,
    get_eval_output,
    init_eval_output,
    load_wrap_log_entries,
    parse_wrapped_data_list,
    set_eval_input,
    wrap,
)

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
