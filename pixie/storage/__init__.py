"""Observation storage module for persisting and querying LLM application traces.

Provides:
- ``Evaluable`` protocol and adapters for uniform evaluator access
- ``ObservationNode`` tree wrapper with traversal and LLM-friendly serialization
- ``ObservationStore`` for persistence and query via Piccolo ORM / SQLite
"""

from __future__ import annotations

from pixie.storage.evaluable import (
    Evaluable,
    LLMSpanEval,
    ObserveSpanEval,
    as_evaluable,
)
from pixie.storage.store import ObservationStore
from pixie.storage.tree import ObservationNode, build_tree

__all__ = [
    "Evaluable",
    "LLMSpanEval",
    "ObserveSpanEval",
    "ObservationNode",
    "ObservationStore",
    "as_evaluable",
    "build_tree",
]
