"""pixie.evals — evaluation harness for LLM applications.

Public API:
    - ``Evaluation`` — result dataclass for a single evaluator run
    - ``Evaluator`` — protocol for evaluation callables
    - ``evaluate`` — run one evaluator against one evaluable
    - ``ScoreThreshold`` — configurable pass criteria
    - ``DatasetEntryResult`` — evaluation results for a single dataset entry
    - ``DatasetScorecard`` — per-dataset scorecard with non-uniform evaluators
    - ``generate_dataset_scorecard_html`` — render a scorecard as HTML
    - ``save_dataset_scorecard`` — write scorecard HTML to disk

Pre-made evaluators (autoevals adapters):
    - ``AutoevalsAdapter`` — generic wrapper for any autoevals ``Scorer``
    - ``LevenshteinMatch`` — edit-distance string similarity
    - ``ExactMatch`` — exact value comparison
    - ``NumericDiff`` — normalised numeric difference
    - ``JSONDiff`` — structural JSON comparison
    - ``ValidJSON`` — JSON syntax / schema validation
    - ``ListContains`` — list overlap
    - ``EmbeddingSimilarity`` — embedding cosine similarity
    - ``Factuality`` — LLM factual accuracy check
    - ``ClosedQA`` — closed-book QA evaluation
    - ``Battle`` — head-to-head comparison
    - ``Humor`` — humor detection
    - ``Security`` — security vulnerability check
    - ``Sql`` — SQL equivalence
    - ``Summary`` — summarisation quality
    - ``Translation`` — translation quality
    - ``Possible`` — feasibility check
    - ``Moderation`` — content moderation
    - ``ContextRelevancy`` — RAGAS context relevancy
    - ``Faithfulness`` — RAGAS faithfulness
    - ``AnswerRelevancy`` — RAGAS answer relevancy
    - ``AnswerCorrectness`` — RAGAS answer correctness

Dataset JSON Format
-------------------

::

    {
      "name": "customer-faq",
      "runnable": "pixie_qa/scripts/run_app.py:run_app",
      "evaluators": ["Factuality"],
      "entries": [
        {
          "entry_kwargs": {"question": "Hello"},
          "test_case": {
            "description": "Basic greeting",
            "eval_input": [{"name": "input", "value": "Hello"}],
            "expectation": "Hi, how can I help?"
          }
        }
      ]
    }

Fields:

- ``runnable`` (required): ``filepath:callable_name`` reference to the function
  that produces ``eval_output`` from ``entry_kwargs``.
- ``evaluators`` (optional): Dataset-level default evaluator names. Applied to
  entries without row-level evaluators.
- ``entries[].evaluators`` (optional): Row-level evaluator names. Use ``"..."`` to
  include dataset defaults.
- ``entries[].entry_kwargs`` (required): Dict of arguments passed to the runnable.
- ``entries[].test_case.description`` (required): Human-readable label for the test case.
- ``entries[].test_case.eval_input`` (required): List of ``NamedData`` items
  (each ``{"name": ..., "value": ...}``).
- ``entries[].test_case.expectation`` (optional): Reference value for comparison-based
  evaluators.

Evaluator Name Resolution
--------------------------

In dataset JSON, evaluator names are resolved as follows:

- **Built-in names** (bare names like ``"Factuality"``, ``"ExactMatch"``) are
  resolved to ``pixie.{Name}`` automatically.
- **Custom evaluators** use ``filepath:callable_name`` format
  (e.g. ``"pixie_qa/evaluators.py:my_evaluator"``).
- Custom evaluator references point to module-level callables — classes
  (instantiated automatically), factory functions (called if zero-arg),
  evaluator functions (used as-is), or pre-instantiated callables (e.g.
  ``create_llm_evaluator`` results — used as-is).

CLI Commands
------------

| Command | Description |
| --- | --- |
| ``pixie test [path] [-v] [--no-open]`` | Run eval tests on dataset files |
| ``pixie analyze <test_run_id>`` | Generate analysis and recommendations |
"""

from pixie.evals.criteria import ScoreThreshold
from pixie.evals.evaluation import Evaluation, Evaluator, evaluate
from pixie.evals.scorecard import (
    DatasetEntryResult,
    DatasetScorecard,
    generate_dataset_scorecard_html,
    save_dataset_scorecard,
)
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

__all__ = [
    "AnswerCorrectness",
    "AnswerRelevancy",
    "AutoevalsAdapter",
    "Battle",
    "ClosedQA",
    "ContextRelevancy",
    "DatasetEntryResult",
    "DatasetScorecard",
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
    "ScoreThreshold",
    "Security",
    "Sql",
    "Summary",
    "Translation",
    "ValidJSON",
    "evaluate",
    "generate_dataset_scorecard_html",
    "save_dataset_scorecard",
]
