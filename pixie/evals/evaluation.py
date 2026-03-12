"""Evaluation primitives: Evaluation result, Evaluator protocol, evaluate()."""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from pixie.storage.evaluable import Evaluable
from pixie.storage.tree import ObservationNode

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Evaluation:
    """The result of a single evaluator applied to a single test case.

    Attributes:
        score: Evaluation score between 0.0 and 1.0.
        reasoning: Human-readable explanation (required).
        details: Arbitrary JSON-serializable metadata.
    """

    score: float
    reasoning: str
    details: dict[str, Any] = field(default_factory=dict)


class Evaluator(Protocol):
    """Protocol for evaluation callables.

    An evaluator is any callable (async or sync) matching this signature.
    Plain async functions, class instances with ``__call__``, or closures
    all satisfy this protocol. Sync evaluators are automatically wrapped
    via ``asyncio.to_thread`` at call time.
    """

    async def __call__(
        self,
        evaluable: Evaluable,
        *,
        trace: list[ObservationNode] | None = None,
    ) -> Evaluation: ...


def _is_async_callable(obj: object) -> bool:
    """Return True if *obj* is an async callable (function or __call__ method)."""
    if inspect.iscoroutinefunction(obj):
        return True
    if callable(obj):
        # For class instances with async __call__, inspect the type's method
        method = type(obj).__dict__.get("__call__")
        return method is not None and inspect.iscoroutinefunction(method)
    return False


async def evaluate(
    evaluator: Callable[..., Any],
    evaluable: Evaluable,
    *,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
    """Run a single evaluator against a single evaluable.

    Behavior:
        1. If *evaluator* is sync, wrap via ``asyncio.to_thread``.
        2. Call evaluator with *evaluable* and *trace*.
        3. Clamp returned ``score`` to [0.0, 1.0].
        4. If evaluator raises, the exception propagates to the caller.
           Evaluator errors (missing API keys, network failures, etc.)
           are never silently converted to a zero score.

    Args:
        evaluator: An evaluator callable (sync or async).
        evaluable: The data to evaluate.
        trace: Optional trace tree forwarded to the evaluator.

    Raises:
        Exception: Any exception raised by the evaluator propagates
            unchanged so callers see clear, actionable errors.
    """
    extra_kwargs: dict[str, Any] = {"trace": trace}

    if _is_async_callable(evaluator):
        result: Evaluation = await evaluator(evaluable, **extra_kwargs)
    else:
        result = await asyncio.to_thread(evaluator, evaluable, **extra_kwargs)

    # Clamp score to [0.0, 1.0]
    clamped_score = result.score
    if clamped_score > 1.0:
        logger.warning("Evaluator returned score %.2f > 1.0, clamping.", clamped_score)
        clamped_score = 1.0
    elif clamped_score < 0.0:
        logger.warning("Evaluator returned score %.2f < 0.0, clamping.", clamped_score)
        clamped_score = 0.0

    if clamped_score != result.score:
        return Evaluation(
            score=clamped_score,
            reasoning=result.reasoning,
            details=result.details,
        )
    return result
