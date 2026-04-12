"""pixie.eval — evaluation framework for LLM applications.

Core API:
    - :class:`Evaluation` — result dataclass for a single evaluator run.
    - :class:`Evaluator` — protocol for evaluation callables.
    - :func:`evaluate` — run one evaluator against one :class:`Evaluable`.

Pre-made evaluators (``autoevals`` adapters):
    - :class:`AutoevalsAdapter` — generic wrapper for any autoevals ``Scorer``.
    - :func:`LevenshteinMatch` — edit-distance string similarity.
    - :func:`ExactMatch` — exact value comparison.
    - :func:`NumericDiff` — normalised numeric difference.
    - :func:`JSONDiff` — structural JSON comparison.
    - :func:`ValidJSON` — JSON syntax / schema validation.
    - :func:`ListContains` — list overlap.
    - :func:`EmbeddingSimilarity` — embedding cosine similarity.
    - :func:`Factuality` — LLM factual accuracy check.
    - :func:`ClosedQA` — closed-book QA evaluation.
    - :func:`Battle` — head-to-head comparison.
    - :func:`Humor` — humor detection.
    - :func:`Security` — security vulnerability check.
    - :func:`Sql` — SQL equivalence.
    - :func:`Summary` — summarisation quality.
    - :func:`Translation` — translation quality.
    - :func:`Possible` — feasibility check.
    - :func:`Moderation` — content moderation.
    - :func:`ContextRelevancy` — RAGAS context relevancy.
    - :func:`Faithfulness` — RAGAS faithfulness.
    - :func:`AnswerRelevancy` — RAGAS answer relevancy.
    - :func:`AnswerCorrectness` — RAGAS answer correctness.

Dataset JSON Format
-------------------

::

    {
      "name": "customer-faq",
      "runnable": "pixie_qa/scripts/run_app.py:run_app",
      "evaluators": ["Factuality"],
      "entries": [
        {
          "input_data": {"question": "Hello"},
          "description": "Basic greeting",
          "eval_input": [{"name": "input", "value": "Hello"}],
          "expectation": "Hi, how can I help?"
        }
      ]
    }

Fields:

- ``runnable`` (required): ``filepath:callable_name`` reference to the function
  that produces ``eval_output`` from ``input_data``.
- ``evaluators`` (optional): Dataset-level default evaluator names. Applied to
  entries without row-level evaluators.
- ``entries[].evaluators`` (optional): Row-level evaluator names. Use ``"..."`` to
  include dataset defaults.
- ``entries[].input_data`` (required): Dict of arguments passed to the runnable.
- ``entries[].description`` (required): Human-readable label for the test case.
- ``entries[].eval_input`` (required): List of ``NamedData`` items
  (each ``{"name": ..., "value": ...}``).
- ``entries[].expectation`` (optional): Reference value for comparison-based
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

from pixie.eval.evaluation import Evaluation, Evaluator, evaluate
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

__all__ = [
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
    "evaluate",
]
