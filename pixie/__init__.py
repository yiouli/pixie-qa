"""pixie — automated quality assurance for AI applications.

Re-exports the full public API so users can ``from pixie import ...``
for every commonly used symbol without needing submodule paths.
"""

from pixie.eval.evaluable import Evaluable, TestCase
from pixie.eval.evaluation import Evaluation, Evaluator, evaluate
from pixie.eval.llm_evaluator import create_llm_evaluator
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
    WrappedData,
    wrap,
)

__all__ = [
    # Instrumentation
    "WrappedData",
    "flush",
    "enable_llm_tracing",
    "add_handler",
    "remove_handler",
    "wrap",
    # Evals
    "AnswerCorrectness",
    "AnswerRelevancy",
    "AutoevalsAdapter",
    "Battle",
    "ClosedQA",
    "remove_handler",
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
    "Security",
    "Sql",
    "Summary",
    "Translation",
    "ValidJSON",
    "create_llm_evaluator",
    "evaluate",
    "Evaluable",
    "TestCase",
]
