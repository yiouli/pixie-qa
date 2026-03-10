"""Evaluable protocol and span adapters for uniform evaluator access."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pixie.instrumentation.spans import (
    AssistantMessage,
    LLMSpan,
    ObserveSpan,
    TextContent,
)


@runtime_checkable
class Evaluable(Protocol):
    """Uniform interface for evaluators to extract data from either span type."""

    @property
    def eval_input(self) -> Any:
        """The primary input to the observed operation."""
        ...  # pragma: no cover

    @property
    def eval_output(self) -> Any:
        """The primary output of the observed operation."""
        ...  # pragma: no cover

    @property
    def eval_metadata(self) -> dict[str, Any]:
        """Supplementary metadata about the observed operation."""
        ...  # pragma: no cover


class ObserveSpanEval:
    """Adapter wrapping an ``ObserveSpan`` to satisfy ``Evaluable``."""

    def __init__(self, span: ObserveSpan) -> None:
        self._span = span

    @property
    def eval_input(self) -> Any:
        """Return ``span.input``."""
        return self._span.input

    @property
    def eval_output(self) -> Any:
        """Return ``span.output``."""
        return self._span.output

    @property
    def eval_metadata(self) -> dict[str, Any]:
        """Return ``span.metadata``."""
        return self._span.metadata


class LLMSpanEval:
    """Adapter wrapping an ``LLMSpan`` to satisfy ``Evaluable``."""

    def __init__(self, span: LLMSpan) -> None:
        self._span = span

    @property
    def eval_input(self) -> tuple[Any, ...]:
        """Return the full ``input_messages`` tuple."""
        return self._span.input_messages

    @property
    def eval_output(self) -> str | None:
        """Extract text from the last output message, or ``None``."""
        if not self._span.output_messages:
            return None
        last: AssistantMessage = self._span.output_messages[-1]
        parts = [p.text for p in last.content if isinstance(p, TextContent)]
        return "".join(parts) if parts else None

    @property
    def eval_metadata(self) -> dict[str, Any]:
        """Return LLM-specific metadata dict."""
        return {
            "provider": self._span.provider,
            "request_model": self._span.request_model,
            "response_model": self._span.response_model,
            "operation": self._span.operation,
            "input_tokens": self._span.input_tokens,
            "output_tokens": self._span.output_tokens,
            "cache_read_tokens": self._span.cache_read_tokens,
            "cache_creation_tokens": self._span.cache_creation_tokens,
            "finish_reasons": self._span.finish_reasons,
            "error_type": self._span.error_type,
            "tool_definitions": self._span.tool_definitions,
        }


def as_evaluable(span: ObserveSpan | LLMSpan) -> Evaluable:
    """Return the appropriate ``Evaluable`` adapter for *span*."""
    if isinstance(span, LLMSpan):
        return LLMSpanEval(span)
    return ObserveSpanEval(span)
