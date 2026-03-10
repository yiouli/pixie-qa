"""Tests for pixie.storage.evaluable — Evaluable protocol and adapters."""

from __future__ import annotations

from pixie.instrumentation.spans import LLMSpan, ObserveSpan
from pixie.storage.evaluable import (
    Evaluable,
    LLMSpanEval,
    ObserveSpanEval,
    as_evaluable,
)


class TestObserveSpanEval:
    """Tests for ObserveSpanEval adapter."""

    def test_satisfies_evaluable(self, sample_observe_span: ObserveSpan) -> None:
        wrapper = ObserveSpanEval(sample_observe_span)
        assert isinstance(wrapper, Evaluable)

    def test_eval_input_returns_span_input(
        self, sample_observe_span: ObserveSpan
    ) -> None:
        wrapper = ObserveSpanEval(sample_observe_span)
        assert wrapper.eval_input == {"query": "What is our refund policy?"}

    def test_eval_output_returns_span_output(
        self, sample_observe_span: ObserveSpan
    ) -> None:
        wrapper = ObserveSpanEval(sample_observe_span)
        assert wrapper.eval_output == "You can return items within 30 days."

    def test_eval_metadata_returns_span_metadata(
        self, sample_observe_span: ObserveSpan
    ) -> None:
        wrapper = ObserveSpanEval(sample_observe_span)
        assert wrapper.eval_metadata == {"env": "test"}


class TestLLMSpanEval:
    """Tests for LLMSpanEval adapter."""

    def test_satisfies_evaluable(self, sample_llm_span: LLMSpan) -> None:
        wrapper = LLMSpanEval(sample_llm_span)
        assert isinstance(wrapper, Evaluable)

    def test_eval_input_returns_input_messages(self, sample_llm_span: LLMSpan) -> None:
        wrapper = LLMSpanEval(sample_llm_span)
        assert wrapper.eval_input == sample_llm_span.input_messages

    def test_eval_output_returns_joined_text(self, sample_llm_span: LLMSpan) -> None:
        wrapper = LLMSpanEval(sample_llm_span)
        assert wrapper.eval_output == "You can return items within 30 days."

    def test_eval_output_returns_none_when_empty(
        self, sample_llm_span_empty_output: LLMSpan
    ) -> None:
        wrapper = LLMSpanEval(sample_llm_span_empty_output)
        assert wrapper.eval_output is None

    def test_eval_metadata_contains_expected_keys(
        self, sample_llm_span: LLMSpan
    ) -> None:
        wrapper = LLMSpanEval(sample_llm_span)
        meta = wrapper.eval_metadata
        assert meta["provider"] == "openai"
        assert meta["request_model"] == "gpt-4o"
        assert meta["response_model"] == "gpt-4o-2025-01-01"
        assert meta["operation"] == "chat"
        assert meta["input_tokens"] == 150
        assert meta["output_tokens"] == 42
        assert meta["cache_read_tokens"] == 30
        assert meta["cache_creation_tokens"] == 0
        assert meta["finish_reasons"] == ("stop",)
        assert meta["error_type"] is None
        assert meta["tool_definitions"] == ()


class TestAsEvaluable:
    """Tests for as_evaluable helper."""

    def test_returns_observe_eval_for_observe_span(
        self, sample_observe_span: ObserveSpan
    ) -> None:
        result = as_evaluable(sample_observe_span)
        assert isinstance(result, ObserveSpanEval)

    def test_returns_llm_eval_for_llm_span(self, sample_llm_span: LLMSpan) -> None:
        result = as_evaluable(sample_llm_span)
        assert isinstance(result, LLMSpanEval)
