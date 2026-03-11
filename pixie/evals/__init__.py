"""pixie.evals — evaluation harness for LLM applications.

Public API:
    - ``Evaluation`` — result dataclass for a single evaluator run
    - ``Evaluator`` — protocol for evaluation callables
    - ``evaluate`` — run one evaluator against one evaluable
    - ``run_and_evaluate`` — evaluate spans from a MemoryTraceHandler
    - ``assert_pass`` — batch evaluation with pass/fail criteria
    - ``EvalAssertionError`` — raised when assert_pass fails
    - ``capture_traces`` — context manager for in-memory trace capture
    - ``MemoryTraceHandler`` — InstrumentationHandler that collects spans
    - ``ScoreThreshold`` — configurable pass criteria
    - ``last_llm_call`` / ``root`` — trace-to-evaluable helpers
"""

from pixie.evals.criteria import ScoreThreshold
from pixie.evals.eval_utils import EvalAssertionError, assert_pass, run_and_evaluate
from pixie.evals.evaluation import Evaluation, Evaluator, evaluate
from pixie.evals.trace_capture import MemoryTraceHandler, capture_traces
from pixie.evals.trace_helpers import last_llm_call, root

__all__ = [
    "EvalAssertionError",
    "Evaluation",
    "Evaluator",
    "MemoryTraceHandler",
    "ScoreThreshold",
    "assert_pass",
    "capture_traces",
    "evaluate",
    "last_llm_call",
    "root",
    "run_and_evaluate",
]
