"""_SpanContext — the mutable object yielded by log()."""

from __future__ import annotations

from datetime import datetime, timezone
from time import time_ns
from typing import Any

from opentelemetry.trace import Span

from .spans import ObserveSpan


def _extract_parent_span_id(otel_span: Span) -> str | None:
    """Extract parent span ID from an OTel span, if present."""
    parent = getattr(otel_span, "parent", None)
    if parent is not None:
        return format(parent.span_id, "016x")
    return None


class _SpanContext:
    """Mutable object yielded by log(). Users interact with this inside the with block.

    Not exported — users only need set_output() and set_metadata().
    The frozen ObserveSpan delivered to the handler is the public type.
    """

    def __init__(self, otel_span: Span, input: Any) -> None:  # noqa: A002
        self._otel_span = otel_span
        self._input = input
        self._output: Any = None
        self._metadata: dict[str, Any] = {}
        self._error: str | None = None

    def set_output(self, value: Any) -> None:
        """Set the output value for this observed block."""
        self._output = value

    def set_metadata(self, key: str, value: Any) -> None:
        """Accumulate a metadata key-value pair."""
        self._metadata[key] = value

    def _snapshot(self) -> ObserveSpan:
        """Produce a frozen ObserveSpan from the current mutable state."""
        ctx = self._otel_span.get_span_context()
        start_ns = getattr(self._otel_span, "start_time", None) or 0
        end_ns = getattr(self._otel_span, "end_time", None) or time_ns()
        return ObserveSpan(
            span_id=format(ctx.span_id, "016x"),
            trace_id=format(ctx.trace_id, "032x"),
            parent_span_id=_extract_parent_span_id(self._otel_span),
            started_at=datetime.fromtimestamp(start_ns / 1e9, tz=timezone.utc),
            ended_at=datetime.fromtimestamp(end_ns / 1e9, tz=timezone.utc),
            duration_ms=(end_ns - start_ns) / 1e6,
            name=getattr(self._otel_span, "name", None),
            input=self._input,
            output=self._output,
            metadata=dict(self._metadata),
            error=self._error,
        )
