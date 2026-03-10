"""ObservationNode tree wrapper with traversal and LLM-friendly serialization."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from pixie.instrumentation.spans import (
    AssistantMessage,
    LLMSpan,
    ObserveSpan,
    SystemMessage,
    TextContent,
    ToolResultMessage,
    UserMessage,
)


@dataclass
class ObservationNode:
    """Tree node wrapping a span with children for hierarchical traversal."""

    span: ObserveSpan | LLMSpan
    children: list[ObservationNode] = field(default_factory=list)

    # ── Delegated properties ──────────────────────────────────────────────

    @property
    def span_id(self) -> str:
        """Span identifier."""
        return self.span.span_id

    @property
    def trace_id(self) -> str:
        """Trace identifier."""
        return self.span.trace_id

    @property
    def parent_span_id(self) -> str | None:
        """Parent span identifier."""
        return self.span.parent_span_id

    @property
    def name(self) -> str:
        """Human-readable name: ``span.name`` for observe, ``request_model`` for LLM."""
        if isinstance(self.span, LLMSpan):
            return self.span.request_model
        return self.span.name or "(unnamed)"

    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds."""
        return self.span.duration_ms

    # ── Search ────────────────────────────────────────────────────────────

    def find(self, name: str) -> list[ObservationNode]:
        """Return all nodes in the subtree where ``node.name == name`` (DFS)."""
        result: list[ObservationNode] = []
        if self.name == name:
            result.append(self)
        for child in self.children:
            result.extend(child.find(name))
        return result

    def find_by_type(self, span_type: type[ObserveSpan] | type[LLMSpan]) -> list[ObservationNode]:
        """Return all nodes in the subtree where ``isinstance(node.span, span_type)``."""
        result: list[ObservationNode] = []
        if isinstance(self.span, span_type):
            result.append(self)
        for child in self.children:
            result.extend(child.find_by_type(span_type))
        return result

    # ── Serialization ─────────────────────────────────────────────────────

    def to_text(self, indent: int = 0) -> str:
        """Serialize the tree to an LLM-friendly indented outline."""
        prefix = "  " * indent
        if isinstance(self.span, LLMSpan):
            return self._llm_to_text(prefix, indent)
        return self._observe_to_text(prefix, indent)

    def _observe_to_text(self, prefix: str, indent: int) -> str:
        span: ObserveSpan = self.span  # type: ignore[assignment]
        lines: list[str] = []
        name = span.name or "(unnamed)"
        lines.append(f"{prefix}{name} [{span.duration_ms:.0f}ms]")
        if span.input is not None:
            lines.append(f"{prefix}  input: {_format_value(span.input)}")
        if span.output is not None:
            lines.append(f"{prefix}  output: {_format_value(span.output)}")
        if span.error is not None:
            lines.append(f"{prefix}  <e>{span.error}</e>")
        if span.metadata:
            lines.append(f"{prefix}  metadata: {json.dumps(span.metadata, default=str)}")
        for child in self.children:
            lines.append(child.to_text(indent + 1))
        return "\n".join(lines)

    def _llm_to_text(self, prefix: str, indent: int) -> str:
        span: LLMSpan = self.span  # type: ignore[assignment]
        lines: list[str] = []
        lines.append(f"{prefix}{span.request_model} [{span.provider}, {span.duration_ms:.0f}ms]")

        # Input messages
        if span.input_messages:
            lines.append(f"{prefix}  input_messages:")
            for msg in span.input_messages:
                lines.append(f"{prefix}    {_format_message(msg)}")

        # Output messages
        if span.output_messages:
            lines.append(f"{prefix}  output:")
            for msg in span.output_messages:
                lines.append(f"{prefix}    {_format_message(msg)}")

        # Tokens
        token_parts: list[str] = []
        if span.input_tokens > 0 or span.output_tokens > 0:
            token_parts.append(f"{span.input_tokens} in / {span.output_tokens} out")
            if span.cache_read_tokens > 0:
                token_parts.append(f"({span.cache_read_tokens} cache read)")
            if span.cache_creation_tokens > 0:
                token_parts.append(f"({span.cache_creation_tokens} cache creation)")
            lines.append(f"{prefix}  tokens: {' '.join(token_parts)}")

        # Error
        if span.error_type is not None:
            lines.append(f"{prefix}  <e>{span.error_type}</e>")

        # Tool definitions
        if span.tool_definitions:
            tool_names = ", ".join(td.name for td in span.tool_definitions)
            lines.append(f"{prefix}  tools: [{tool_names}]")

        for child in self.children:
            lines.append(child.to_text(indent + 1))
        return "\n".join(lines)


def _format_value(value: Any) -> str:
    """Format a value for text output."""
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return str(value)


def _format_message(
    msg: SystemMessage | UserMessage | AssistantMessage | ToolResultMessage,
) -> str:
    """Format a single message for text output."""
    if isinstance(msg, SystemMessage):
        return f"system: {msg.content}"
    if isinstance(msg, UserMessage):
        parts = [p.text for p in msg.content if isinstance(p, TextContent)]
        return f"user: {''.join(parts)}"
    if isinstance(msg, AssistantMessage):
        parts = [p.text for p in msg.content if isinstance(p, TextContent)]
        text = f"assistant: {''.join(parts)}"
        if msg.tool_calls:
            names = ", ".join(tc.name for tc in msg.tool_calls)
            text += f" [tool_calls: {names}]"
        return text
    if isinstance(msg, ToolResultMessage):
        return f"tool({msg.tool_name}): {msg.content}"
    return str(msg)  # pragma: no cover


def build_tree(spans: list[ObserveSpan | LLMSpan]) -> list[ObservationNode]:
    """Build a tree from a flat list of spans sharing the same trace.

    Algorithm:
    1. Create an ``ObservationNode`` for each span.
    2. Index by ``span.span_id``.
    3. Link children to parents via ``parent_span_id``.
    4. Orphaned nodes (missing parent) become roots.
    5. Sort each node's children by ``started_at`` ascending.
    6. Return list of root nodes.
    """
    nodes: dict[str, ObservationNode] = {}
    for span in spans:
        nodes[span.span_id] = ObservationNode(span=span)

    roots: list[ObservationNode] = []
    for node in nodes.values():
        pid = node.span.parent_span_id
        if pid is not None and pid in nodes:
            nodes[pid].children.append(node)
        else:
            roots.append(node)

    # Sort children by started_at
    for node in nodes.values():
        node.children.sort(key=lambda n: n.span.started_at)

    roots.sort(key=lambda n: n.span.started_at)
    return roots
