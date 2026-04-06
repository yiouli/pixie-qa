"""Evaluable model — uniform data carrier for evaluators.

``Evaluable`` is a frozen Pydantic ``BaseModel`` that serves as the uniform
data carrier for evaluators.  The ``_Unset`` sentinel distinguishes *"expected
output was never provided"* from *"expected output is explicitly None"*.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class _Unset(Enum):
    """Sentinel to distinguish 'not provided' from ``None``."""

    UNSET = "UNSET"


UNSET = _Unset.UNSET
"""Sentinel value: field was never set (as opposed to explicitly ``None``)."""


class Evaluable(BaseModel):
    """Uniform data carrier for evaluators.

    All fields use Pydantic ``JsonValue`` to guarantee JSON
    round-trip fidelity.  ``expected_output`` uses a union with the
    ``_Unset`` sentinel so callers can distinguish *"expected output
    was not provided"* from *"expected output is explicitly None"*.

    Attributes:
        eval_input: The primary input to the observed operation.
        eval_output: The primary output of the observed operation.
        eval_metadata: Supplementary metadata (``None`` when absent).
        expected_output: The expected/reference output for evaluation.
            Defaults to ``UNSET`` (not provided). May be explicitly
            set to ``None`` to indicate "there is no expected output".
        captured_output: Captured output data from ``wrap(purpose="output")``,
            keyed by wrap name.
        captured_state: Captured state data from ``wrap(purpose="state")``,
            keyed by wrap name.
    """

    model_config = ConfigDict(frozen=True)

    eval_input: JsonValue = None
    eval_output: JsonValue = None
    eval_metadata: dict[str, JsonValue] | None = None
    expected_output: JsonValue | _Unset = Field(default=UNSET)
    evaluators: list[str] | None = None
    description: str | None = None
    captured_output: dict[str, JsonValue] | None = None
    captured_state: dict[str, JsonValue] | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_unset_sentinel(cls, data: Any) -> Any:
        """Reconstruct ``_Unset`` from the serialised ``"UNSET"`` string."""
        if isinstance(data, dict):
            val = data.get("expected_output")
            if val == "UNSET":
                data = {**data, "expected_output": UNSET}
        return data
