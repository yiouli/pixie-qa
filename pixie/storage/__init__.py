"""Storage module for evaluation data models.

Provides:
- ``Evaluable`` Pydantic BaseModel for uniform evaluator access
- ``UNSET`` sentinel for distinguishing unset from ``None``
"""

from __future__ import annotations

from pixie.storage.evaluable import (
    UNSET,
    Evaluable,
)

__all__ = [
    "Evaluable",
    "UNSET",
]
