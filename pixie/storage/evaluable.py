"""Evaluable model and span-to-evaluable conversion.

``Evaluable`` is a frozen Pydantic ``BaseModel`` that serves as the uniform
data carrier for evaluators.  The ``_Unset`` sentinel distinguishes *"expected
output was never provided"* from *"expected output is explicitly None"*.
"""

from __future__ import annotations

from dataclasses import asdict
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from pixie.instrumentation.spans import (
    AssistantMessage,
    LLMSpan,
    ObserveSpan,
    TextContent,
)


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
    """

    model_config = ConfigDict(frozen=True)

    eval_input: JsonValue = None
    eval_output: JsonValue = None
    eval_metadata: dict[str, JsonValue] | None = None
    expected_output: JsonValue | _Unset = Field(default=UNSET)
    evaluators: list[str] | None = None
    description: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_unset_sentinel(cls, data: Any) -> Any:
        """Reconstruct ``_Unset`` from the serialised ``"UNSET"`` string."""
        if isinstance(data, dict):
            val = data.get("expected_output")
            if val == "UNSET":
                data = {**data, "expected_output": UNSET}
        return data


def as_evaluable(span: ObserveSpan | LLMSpan) -> Evaluable:
    """Build an ``Evaluable`` from a span.

    ``expected_output`` is left as ``UNSET`` — span data never carries
    expected values.
    """
    if isinstance(span, LLMSpan):
        return _llm_span_to_evaluable(span)
    return _observe_span_to_evaluable(span)


def _observe_span_to_evaluable(span: ObserveSpan) -> Evaluable:
    meta: dict[str, Any] = dict(span.metadata) if span.metadata else {}
    meta["trace_id"] = span.trace_id
    meta["span_id"] = span.span_id
    return Evaluable(
        eval_input=span.input,
        eval_output=span.output,
        eval_metadata=meta,
    )


def _make_json_compatible(obj: Any) -> Any:
    """Recursively convert dataclass-derived dicts to JSON-compatible values.

    Converts tuples to lists so Pydantic's ``JsonValue`` validation passes.
    """
    if isinstance(obj, dict):
        return {k: _make_json_compatible(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_json_compatible(item) for item in obj]
    return obj


def _llm_span_to_evaluable(span: LLMSpan) -> Evaluable:
    # Extract text from last output message
    output_text: str | None = None
    if span.output_messages:
        last: AssistantMessage = span.output_messages[-1]
        parts = [p.text for p in last.content if isinstance(p, TextContent)]
        output_text = "".join(parts) if parts else None

    # Convert input_messages to JSON-compatible list of dicts
    input_data: JsonValue = [
        _make_json_compatible(asdict(msg)) for msg in span.input_messages
    ]

    metadata: dict[str, Any] = {
        "trace_id": span.trace_id,
        "span_id": span.span_id,
        "provider": span.provider,
        "request_model": span.request_model,
        "response_model": span.response_model,
        "operation": span.operation,
        "input_tokens": span.input_tokens,
        "output_tokens": span.output_tokens,
        "cache_read_tokens": span.cache_read_tokens,
        "cache_creation_tokens": span.cache_creation_tokens,
        "finish_reasons": list(span.finish_reasons),
        "error_type": span.error_type,
        "tool_definitions": [
            _make_json_compatible(asdict(td)) for td in span.tool_definitions
        ],
    }

    return Evaluable(
        eval_input=input_data,
        eval_output=output_text,
        eval_metadata=metadata,
    )
