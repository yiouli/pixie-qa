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
