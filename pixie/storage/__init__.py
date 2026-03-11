"""Observation storage module for persisting and querying LLM application traces.

Provides:
- ``Evaluable`` Pydantic BaseModel for uniform evaluator access
- ``UNSET`` sentinel for distinguishing unset from ``None``
- ``ObservationNode`` tree wrapper with traversal and LLM-friendly serialization
- ``ObservationStore`` for persistence and query via Piccolo ORM / SQLite
"""

from __future__ import annotations

from pixie.storage.evaluable import (
    UNSET,
    Evaluable,
    as_evaluable,
)
from pixie.storage.store import ObservationStore
from pixie.storage.tree import ObservationNode, build_tree

__all__ = [
    "Evaluable",
    "ObservationNode",
    "ObservationStore",
    "UNSET",
    "as_evaluable",
    "build_tree",
]
