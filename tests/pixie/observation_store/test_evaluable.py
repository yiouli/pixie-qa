"""Tests for pixie.storage.evaluable — Evaluable Pydantic model and as_evaluable()."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pixie.instrumentation.spans import LLMSpan, ObserveSpan
from pixie.storage.evaluable import (
    UNSET,
    Evaluable,
    _Unset,
    as_evaluable,
)


class TestEvaluableConstruction:
    """Tests for Evaluable Pydantic model construction."""

    def test_construction_with_all_fields(self) -> None:
        ev = Evaluable(
            eval_input="hello",
            eval_output="world",
            eval_metadata={"key": "value"},
            expected_output="expected",
        )
        assert ev.eval_input == "hello"
        assert ev.eval_output == "world"
        assert ev.eval_metadata == {"key": "value"}
        assert ev.expected_output == "expected"

    def test_construction_with_defaults(self) -> None:
        ev = Evaluable()
        assert ev.eval_input is None
        assert ev.eval_output is None
        assert ev.eval_metadata is None
        assert ev.expected_output is UNSET

    def test_expected_output_distinguishes_unset_from_none(self) -> None:
        ev_unset = Evaluable()
        ev_none = Evaluable(expected_output=None)
        ev_value = Evaluable(expected_output="answer")

        assert ev_unset.expected_output is UNSET
        assert isinstance(ev_unset.expected_output, _Unset)
        assert ev_none.expected_output is None
        assert ev_value.expected_output == "answer"

    def test_frozen_raises_on_mutation(self) -> None:
        ev = Evaluable(eval_input="hello")
        with pytest.raises(ValidationError):
            ev.eval_input = "mutated"  # type: ignore[misc]

    def test_eval_metadata_accepts_none(self) -> None:
        ev = Evaluable(eval_metadata=None)
        assert ev.eval_metadata is None

    def test_eval_metadata_accepts_dict(self) -> None:
        ev = Evaluable(eval_metadata={"key": "value", "num": 42})
        assert ev.eval_metadata == {"key": "value", "num": 42}


class TestEvaluableSerialisation:
    """Tests for Evaluable model_dump / model_validate round-trip."""

    def test_round_trip_preserves_all_fields(self) -> None:
        ev = Evaluable(
            eval_input="input",
            eval_output="output",
            eval_metadata={"k": "v"},
            expected_output="expected",
        )
        data = ev.model_dump(mode="json")
        restored = Evaluable.model_validate(data)
        assert restored == ev

    def test_round_trip_preserves_unset(self) -> None:
        ev = Evaluable()
        data = ev.model_dump(mode="json")
        restored = Evaluable.model_validate(data)
        assert restored.expected_output is UNSET

    def test_round_trip_preserves_none_expected_output(self) -> None:
        ev = Evaluable(expected_output=None)
        data = ev.model_dump(mode="json")
        restored = Evaluable.model_validate(data)
        assert restored.expected_output is None


class TestAsEvaluableObserveSpan:
    """Tests for as_evaluable() with ObserveSpan."""

    def test_returns_evaluable_instance(self, sample_observe_span: ObserveSpan) -> None:
        result = as_evaluable(sample_observe_span)
        assert isinstance(result, Evaluable)

    def test_eval_input_from_observe_span(self, sample_observe_span: ObserveSpan) -> None:
        result = as_evaluable(sample_observe_span)
        assert result.eval_input == {"query": "What is our refund policy?"}

    def test_eval_output_from_observe_span(self, sample_observe_span: ObserveSpan) -> None:
        result = as_evaluable(sample_observe_span)
        assert result.eval_output == "You can return items within 30 days."

    def test_eval_metadata_from_observe_span(self, sample_observe_span: ObserveSpan) -> None:
        result = as_evaluable(sample_observe_span)
        assert result.eval_metadata == {"env": "test"}

    def test_expected_output_is_unset(self, sample_observe_span: ObserveSpan) -> None:
        result = as_evaluable(sample_observe_span)
        assert result.expected_output is UNSET

    def test_empty_metadata_gives_none(self, sample_observe_span_none_io: ObserveSpan) -> None:
        result = as_evaluable(sample_observe_span_none_io)
        assert result.eval_metadata is None


class TestAsEvaluableLLMSpan:
    """Tests for as_evaluable() with LLMSpan."""

    def test_returns_evaluable_instance(self, sample_llm_span: LLMSpan) -> None:
        result = as_evaluable(sample_llm_span)
        assert isinstance(result, Evaluable)

    def test_eval_output_extracts_text(self, sample_llm_span: LLMSpan) -> None:
        result = as_evaluable(sample_llm_span)
        assert result.eval_output == "You can return items within 30 days."

    def test_eval_output_none_when_empty(self, sample_llm_span_empty_output: LLMSpan) -> None:
        result = as_evaluable(sample_llm_span_empty_output)
        assert result.eval_output is None

    def test_eval_input_is_json_compatible_list(self, sample_llm_span: LLMSpan) -> None:
        result = as_evaluable(sample_llm_span)
        assert isinstance(result.eval_input, list)
        assert len(result.eval_input) == 2  # SystemMessage + UserMessage

    def test_eval_metadata_contains_expected_keys(self, sample_llm_span: LLMSpan) -> None:
        result = as_evaluable(sample_llm_span)
        assert result.eval_metadata is not None
        meta = result.eval_metadata
        assert meta["provider"] == "openai"
        assert meta["request_model"] == "gpt-4o"
        assert meta["response_model"] == "gpt-4o-2025-01-01"
        assert meta["operation"] == "chat"
        assert meta["input_tokens"] == 150
        assert meta["output_tokens"] == 42

    def test_expected_output_is_unset(self, sample_llm_span: LLMSpan) -> None:
        result = as_evaluable(sample_llm_span)
        assert result.expected_output is UNSET
