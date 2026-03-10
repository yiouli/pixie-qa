"""Tests for pixie.storage.tree — ObservationNode and build_tree."""

from __future__ import annotations

from datetime import datetime, timezone

from pixie.instrumentation.spans import (
    LLMSpan,
    ObserveSpan,
)
from pixie.storage.tree import ObservationNode, build_tree


class TestBuildTree:
    """Tests for the build_tree function."""

    def test_single_root(self, sample_observe_span: ObserveSpan) -> None:
        roots = build_tree([sample_observe_span])
        assert len(roots) == 1
        assert roots[0].span is sample_observe_span
        assert roots[0].children == []

    def test_parent_child(
        self,
        sample_observe_span: ObserveSpan,
        sample_llm_span: LLMSpan,
    ) -> None:
        roots = build_tree([sample_observe_span, sample_llm_span])
        assert len(roots) == 1
        assert roots[0].span is sample_observe_span
        assert len(roots[0].children) == 1
        assert roots[0].children[0].span is sample_llm_span

    def test_sorts_children_by_started_at(
        self,
        sample_observe_span: ObserveSpan,
        sample_llm_span: LLMSpan,
        sample_llm_span_with_tools: LLMSpan,
    ) -> None:
        # llm_span starts before llm_span_with_tools
        roots = build_tree(
            [
                sample_llm_span_with_tools,
                sample_observe_span,
                sample_llm_span,
            ]
        )
        assert len(roots) == 1
        children = roots[0].children
        assert len(children) == 2
        assert children[0].span is sample_llm_span
        assert children[1].span is sample_llm_span_with_tools

    def test_orphaned_spans_become_roots(self) -> None:
        orphan = ObserveSpan(
            span_id="0000000000000010",
            trace_id="aaaa0000000000000000000000000001",
            parent_span_id="nonexistent_parent",
            started_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            ended_at=datetime(2025, 1, 1, 12, 0, 1, tzinfo=timezone.utc),
            duration_ms=1000.0,
            name="orphan",
            input=None,
            output=None,
            metadata={},
            error=None,
        )
        roots = build_tree([orphan])
        assert len(roots) == 1
        assert roots[0].name == "orphan"


class TestObservationNodeFind:
    """Tests for find and find_by_type."""

    def test_find_matching_name(
        self,
        sample_observe_span: ObserveSpan,
        sample_llm_span: LLMSpan,
    ) -> None:
        roots = build_tree([sample_observe_span, sample_llm_span])
        results = roots[0].find("gpt-4o")
        assert len(results) == 1
        assert results[0].span is sample_llm_span

    def test_find_nonexistent_returns_empty(self, sample_observe_span: ObserveSpan) -> None:
        roots = build_tree([sample_observe_span])
        assert roots[0].find("nonexistent") == []

    def test_find_by_type_llm(
        self,
        sample_observe_span: ObserveSpan,
        sample_llm_span: LLMSpan,
    ) -> None:
        roots = build_tree([sample_observe_span, sample_llm_span])
        results = roots[0].find_by_type(LLMSpan)
        assert len(results) == 1
        assert results[0].span is sample_llm_span

    def test_find_by_type_observe(
        self,
        sample_observe_span: ObserveSpan,
        sample_llm_span: LLMSpan,
    ) -> None:
        roots = build_tree([sample_observe_span, sample_llm_span])
        results = roots[0].find_by_type(ObserveSpan)
        assert len(results) == 1
        assert results[0].span is sample_observe_span


class TestObservationNodeDelegatedProps:
    """Tests for delegated properties."""

    def test_span_id(self, sample_observe_span: ObserveSpan) -> None:
        node = ObservationNode(span=sample_observe_span)
        assert node.span_id == "aaaa000000000001"

    def test_trace_id(self, sample_observe_span: ObserveSpan) -> None:
        node = ObservationNode(span=sample_observe_span)
        assert node.trace_id == "bbbb0000000000000000000000000001"

    def test_parent_span_id(self, sample_llm_span: LLMSpan) -> None:
        node = ObservationNode(span=sample_llm_span)
        assert node.parent_span_id == "aaaa000000000001"

    def test_name_observe_span(self, sample_observe_span: ObserveSpan) -> None:
        node = ObservationNode(span=sample_observe_span)
        assert node.name == "root_pipeline"

    def test_name_observe_span_unnamed(self, sample_observe_span_none_io: ObserveSpan) -> None:
        node = ObservationNode(span=sample_observe_span_none_io)
        assert node.name == "(unnamed)"

    def test_name_llm_span(self, sample_llm_span: LLMSpan) -> None:
        node = ObservationNode(span=sample_llm_span)
        assert node.name == "gpt-4o"

    def test_duration_ms(self, sample_observe_span: ObserveSpan) -> None:
        node = ObservationNode(span=sample_observe_span)
        assert node.duration_ms == 1000.0


class TestToTextObserveSpan:
    """Tests for to_text with ObserveSpan."""

    def test_basic_format(self, sample_observe_span: ObserveSpan) -> None:
        node = ObservationNode(span=sample_observe_span)
        text = node.to_text()
        assert "root_pipeline [1000ms]" in text
        assert 'input: {"query": "What is our refund policy?"}' in text
        assert "output: You can return items within 30 days." in text
        assert 'metadata: {"env": "test"}' in text

    def test_omits_none_fields(self, sample_observe_span_none_io: ObserveSpan) -> None:
        node = ObservationNode(span=sample_observe_span_none_io)
        text = node.to_text()
        assert "(unnamed) [100ms]" in text
        assert "input:" not in text
        assert "output:" not in text

    def test_error_tag(self) -> None:
        span = ObserveSpan(
            span_id="0000000000000099",
            trace_id="aaaa0000000000000000000000000099",
            parent_span_id=None,
            started_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            ended_at=datetime(2025, 1, 1, 12, 0, 5, tzinfo=timezone.utc),
            duration_ms=5000.0,
            name="failing_pipeline",
            input=None,
            output=None,
            metadata={},
            error="TimeoutError",
        )
        node = ObservationNode(span=span)
        text = node.to_text()
        assert "<e>TimeoutError</e>" in text

    def test_nested_tree_indentation(
        self,
        sample_observe_span: ObserveSpan,
        sample_llm_span: LLMSpan,
    ) -> None:
        roots = build_tree([sample_observe_span, sample_llm_span])
        text = roots[0].to_text()
        lines = text.split("\n")
        # Root at indent 0
        assert lines[0].startswith("root_pipeline")
        # Child at indent 1 (2 spaces)
        llm_lines = [ln for ln in lines if "gpt-4o" in ln and "openai" in ln]
        assert len(llm_lines) == 1
        assert llm_lines[0].startswith("  gpt-4o")


class TestToTextLLMSpan:
    """Tests for to_text with LLMSpan."""

    def test_header_format(self, sample_llm_span: LLMSpan) -> None:
        node = ObservationNode(span=sample_llm_span)
        text = node.to_text()
        assert "gpt-4o [openai, 350ms]" in text

    def test_input_messages(self, sample_llm_span: LLMSpan) -> None:
        node = ObservationNode(span=sample_llm_span)
        text = node.to_text()
        assert "input_messages:" in text
        assert "system: You are a helpful assistant." in text
        assert "user: What is our refund policy?" in text

    def test_output(self, sample_llm_span: LLMSpan) -> None:
        node = ObservationNode(span=sample_llm_span)
        text = node.to_text()
        assert "assistant: You can return items within 30 days." in text

    def test_token_counts(self, sample_llm_span: LLMSpan) -> None:
        node = ObservationNode(span=sample_llm_span)
        text = node.to_text()
        assert "tokens: 150 in / 42 out (30 cache read)" in text

    def test_error_tag(self, sample_llm_span_empty_output: LLMSpan) -> None:
        node = ObservationNode(span=sample_llm_span_empty_output)
        text = node.to_text()
        assert "<e>TimeoutError</e>" in text

    def test_omits_output_when_empty(self, sample_llm_span_empty_output: LLMSpan) -> None:
        node = ObservationNode(span=sample_llm_span_empty_output)
        text = node.to_text()
        assert "output:" not in text

    def test_tool_calls_in_assistant(self, sample_llm_span_with_tools: LLMSpan) -> None:
        node = ObservationNode(span=sample_llm_span_with_tools)
        text = node.to_text()
        assert "[tool_calls: search]" in text

    def test_tool_definitions(self, sample_llm_span_with_tools: LLMSpan) -> None:
        node = ObservationNode(span=sample_llm_span_with_tools)
        text = node.to_text()
        assert "tools: [search]" in text

    def test_user_message_text_parts(self, sample_llm_span_with_image: LLMSpan) -> None:
        node = ObservationNode(span=sample_llm_span_with_image)
        text = node.to_text()
        assert "user: Describe this image" in text

    def test_cache_tokens_shown_when_nonzero(self, sample_llm_span: LLMSpan) -> None:
        node = ObservationNode(span=sample_llm_span)
        text = node.to_text()
        assert "cache read" in text
