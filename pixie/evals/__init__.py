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
      "items": [
        {
          "description": "Basic greeting",
          "eval_input": {"question": "Hello"},
          "expected_output": "Hi, how can I help?"
        }
      ]
    }

Fields:

- ``runnable`` (required): ``filepath:callable_name`` reference to the function
  that produces ``eval_output`` from ``eval_input``.
- ``evaluators`` (optional): Dataset-level default evaluator names. Applied to
  items without row-level evaluators.
- ``items[].evaluators`` (optional): Row-level evaluator names. Use ``"..."`` to
  include dataset defaults.
- ``items[].description`` (required): Human-readable label for the test case.
- ``items[].eval_input`` (required): Input passed to the runnable.
- ``items[].expected_output`` (optional): Reference value for comparison-based
  evaluators.
- ``items[].eval_output`` (optional): Pre-computed output (skips runnable
  execution).

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
| ``pixie dataset create <name>`` | Create a new empty dataset |
| ``pixie dataset list`` | List all datasets |
| ``pixie dataset save <name> [--select MODE]`` | Save a span to a dataset |
| ``pixie dataset validate [path]`` | Validate dataset JSON files |
| ``pixie analyze <test_run_id>`` | Generate analysis and recommendations |
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
from pixie.evals.trace_capture import MemoryTraceHandler, capture_traces
from pixie.evals.trace_helpers import last_llm_call, root

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
    "ScoreThreshold",
    "Security",
    "Sql",
    "Summary",
    "Translation",
    "ValidJSON",
    "assert_dataset_pass",
    "assert_pass",
    "capture_traces",
    "evaluate",
    "generate_dataset_scorecard_html",
    "last_llm_call",
    "root",
    "run_and_evaluate",
    "save_dataset_scorecard",
]
