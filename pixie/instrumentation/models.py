"""Pydantic models for trace log records.

Defines the structured log record types written by ``pixie trace``
and consumed by ``pixie format``:

- :class:`EntryInputLog` — the kwargs record (``type="kwargs"``).
- :class:`LLMSpanLog` — an LLM span record (``type="llm_span"``).

:class:`WrappedData` (from :mod:`pixie.instrumentation.wrap`) is the
model for wrap records (``type="wrap"``).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, JsonValue

ENTRY_KWARGS_KEY: str = "app_input"
"""Reserved eval_input name for the runnable kwargs.

``pixie format`` always adds an :class:`~pixie.eval.evaluable.NamedData`
item with this name to ``eval_input`` so that the dataset entry is valid
even when the app has no ``wrap(purpose='input')`` calls.  Wrap names
must not collide with this key — ``pixie trace`` validates this at write
time.
"""


class EntryInputLog(BaseModel):
    """Kwargs record written at the start of a trace.

    Attributes:
        type: Always ``"kwargs"``.
        value: The runnable kwargs dictionary.
    """

    type: Literal["kwargs"] = "kwargs"
    value: dict[str, JsonValue]


class LLMSpanLog(BaseModel):
    """LLM span record capturing the semantically meaningful fields.

    Metadata-like fields (timing, IDs, token counts) are omitted because
    they are not useful for dataset construction via ``pixie format``.

    Attributes:
        type: Always ``"llm_span"``.
        operation: The LLM operation type (e.g. ``"chat"``).
        provider: LLM provider name (e.g. ``"openai"``).
        request_model: Model name from the request.
        response_model: Model name from the response.
        input_messages: Serialized input messages.
        output_messages: Serialized output messages.
        tool_definitions: Serialized tool definitions.
        finish_reasons: List of finish reasons.
        output_type: Output type string.
        error_type: Error type string.
    """

    type: Literal["llm_span"] = "llm_span"
    operation: str | None = None
    provider: str | None = None
    request_model: str | None = None
    response_model: str | None = None
    input_messages: list[dict[str, Any]] = []
    output_messages: list[dict[str, Any]] = []
    tool_definitions: list[dict[str, Any]] = []
    finish_reasons: list[str] = []
    output_type: str | None = None
    error_type: str | None = None


class LLMSpanTrace(LLMSpanLog):
    """Full LLM span record including timing and token data for trace analysis.

    Extends :class:`LLMSpanLog` with fields needed for trace-based analysis:
    token counts, duration, and timestamps.

    Attributes:
        type: Always ``"llm_span_trace"``.
        input_tokens: Number of input tokens.
        output_tokens: Number of output tokens.
        duration_ms: Call duration in milliseconds.
        started_at: ISO 8601 start timestamp.
        ended_at: ISO 8601 end timestamp.
    """

    type: Literal["llm_span_trace"] = "llm_span_trace"  # type: ignore[assignment]
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: float = 0.0
    started_at: str | None = None
    ended_at: str | None = None
