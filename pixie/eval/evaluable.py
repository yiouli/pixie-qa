"""Evaluable model — uniform data carrier for evaluators.

``TestCase`` defines the scenario (input, expectation, metadata) without
the actual output.  ``Evaluable`` extends it with actual output.
``NamedData`` provides a name+value pair for structured evaluation data.

The ``_Unset`` sentinel distinguishes *"expectation was never provided"*
from *"expectation is explicitly None"*.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, JsonValue, model_validator


class _Unset(Enum):
    """Sentinel to distinguish 'not provided' from ``None``."""

    UNSET = "UNSET"


UNSET = _Unset.UNSET
"""Sentinel value: field was never set (as opposed to explicitly ``None``)."""


class NamedData(BaseModel):
    """A named data value for evaluation input/output.

    Attributes:
        name: Identifier for this data item.
        value: The JSON-serializable value.
    """

    name: str
    value: JsonValue


class TestCase(BaseModel):
    """Scenario definition without actual output.

    Defines the input, expectation, and metadata for a test case.
    Does not include the actual output — use ``Evaluable`` for that.

    Attributes:
        eval_input: Named input data items.  May be empty in
            ``DatasetEntry`` — the runner prepends ``input_data``
            when building the ``Evaluable``.
        expectation: Expected/reference output for evaluation.
            Defaults to ``UNSET`` (not provided). May be explicitly
            set to ``None`` to indicate "no expectation".
        eval_metadata: Supplementary metadata (``None`` when absent).
        description: Human-readable description.
    """

    eval_input: list[NamedData] = []
    expectation: JsonValue | _Unset = Field(default=UNSET)
    eval_metadata: dict[str, JsonValue] | None = None
    description: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_unset_sentinel(cls, data: Any) -> Any:
        """Reconstruct ``_Unset`` from the serialised ``"UNSET"`` string."""
        if isinstance(data, dict):
            val = data.get("expectation")
            if val == "UNSET":
                data = {**data, "expectation": UNSET}
        return data


class Evaluable(TestCase):
    """TestCase plus actual output — the full data carrier for evaluators.

    Inherits all ``TestCase`` fields and adds ``eval_output``.

    The runner guarantees ``eval_input`` is non-empty by prepending
    ``input_data`` before constructing an ``Evaluable``.

    Attributes:
        eval_output: Named output data items from the observed operation
            (non-empty).
    """

    eval_output: list[NamedData] = Field(min_length=1)

    @model_validator(mode="after")
    def _require_eval_input(self) -> Evaluable:
        """Evaluators always need at least one input item."""
        if not self.eval_input:
            raise ValueError("eval_input must be non-empty for Evaluable")
        return self


def collapse_named_data(items: list[NamedData]) -> JsonValue:
    """Collapse a list of :class:`NamedData` into a single JSON value.

    - Empty list → ``None``
    - Single item → that item's ``value`` (preserves type)
    - Multiple items → ``dict`` mapping ``name → value``

    This is the canonical way to convert ``eval_input`` or
    ``eval_output`` to a scalar suitable for evaluators, display,
    or token estimation.
    """
    if not items:
        return None
    if len(items) == 1:
        return items[0].value
    return {item.name: item.value for item in items}
