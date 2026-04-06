"""Storage module for evaluation data models.

Provides:
- ``NamedData`` named value for evaluation input/output
- ``TestCase`` scenario definition (input + expectation, no output)
- ``Evaluable`` TestCase plus actual output — full evaluator data carrier
- ``UNSET`` sentinel for distinguishing unset from ``None``
"""

from __future__ import annotations

from pixie.storage.evaluable import (
    UNSET,
    Evaluable,
    NamedData,
    TestCase,
)

__all__ = [
    "Evaluable",
    "NamedData",
    "TestCase",
    "UNSET",
]
