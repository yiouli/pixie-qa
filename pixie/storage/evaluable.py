"""Evaluable model and span-to-evaluable conversion.

``Evaluable`` is a frozen Pydantic ``BaseModel`` that serves as the uniform
data carrier for evaluators.  The ``_Unset`` sentinel distinguishes *"expected
output was never provided"* from *"expected output is explicitly None"*.
"""

from __future__ import annotations

from dataclasses import asdict
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic import JsonValue

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


def as_evaluable(span: ObserveSpan | LLMSpan) -> Evaluable:
    """Build an ``Evaluable`` from a span.

    ``expected_output`` is left as ``UNSET`` — span data never carries
    expected values.
    """
    if isinstance(span, LLMSpan):
        return _llm_span_to_evaluable(span)
    return _observe_span_to_evaluable(span)


def _observe_span_to_evaluable(span: ObserveSpan) -> Evaluable:
    return Evaluable(
        eval_input=span.input,
        eval_output=span.output,
        eval_metadata=span.metadata if span.metadata else None,
    )


def _llm_span_to_evaluable(span: LLMSpan) -> Evaluable:
    # Extract text from last output message
    output_text: str | None = None
    if span.output_messages:
        last: AssistantMessage = span.output_messages[-1]
        parts = [p.text for p in last.content if isinstance(p, TextContent)]
        output_text = "".join(parts) if parts else None

    # Convert input_messages to JSON-compatible list of dicts
    input_data: list[dict[str, Any]] = [asdict(msg) for msg in span.input_messages]

    metadata: dict[str, Any] = {
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
        "tool_definitions": [asdict(td) for td in span.tool_definitions],
    }

    return Evaluable(
        eval_input=input_data,
        eval_output=output_text,
        eval_metadata=metadata,
    )
