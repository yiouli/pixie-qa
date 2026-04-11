"""Tests for pixie.eval.agent_evaluator — agent-deferred evaluators."""

from __future__ import annotations

import asyncio

import pytest

from pixie.eval.agent_evaluator import (
    AgentEvaluationPending,
    _AgentEvaluator,
    create_agent_evaluator,
)
from pixie.eval.evaluable import UNSET, Evaluable, NamedData


def _ev() -> Evaluable:
    return Evaluable(
        eval_input=[NamedData(name="input", value="test")],
        eval_output=[NamedData(name="output", value="result")],
        expectation=UNSET,
        eval_metadata=None,
        description=None,
    )


class TestAgentEvaluationPending:
    """Tests for AgentEvaluationPending exception."""

    def test_stores_evaluator_name(self) -> None:
        exc = AgentEvaluationPending("ResponseQuality", "Be helpful")
        assert exc.evaluator_name == "ResponseQuality"

    def test_stores_criteria(self) -> None:
        exc = AgentEvaluationPending("ResponseQuality", "Be helpful")
        assert exc.criteria == "Be helpful"

    def test_str_includes_evaluator_name(self) -> None:
        exc = AgentEvaluationPending("ResponseQuality", "Be helpful")
        assert "ResponseQuality" in str(exc)

    def test_is_exception(self) -> None:
        exc = AgentEvaluationPending("ResponseQuality", "Be helpful")
        assert isinstance(exc, Exception)


class TestCreateAgentEvaluator:
    """Tests for create_agent_evaluator factory."""

    def test_returns_agent_evaluator_instance(self) -> None:
        evaluator = create_agent_evaluator(
            name="ResponseQuality",
            criteria="Rate the response quality.",
        )
        assert isinstance(evaluator, _AgentEvaluator)

    def test_name_property(self) -> None:
        evaluator = create_agent_evaluator(
            name="ResponseQuality",
            criteria="Rate the response quality.",
        )
        assert evaluator.name == "ResponseQuality"

    def test_call_raises_agent_evaluation_pending(self) -> None:
        evaluator = create_agent_evaluator(
            name="ResponseQuality",
            criteria="Rate the response quality.",
        )
        with pytest.raises(AgentEvaluationPending) as exc_info:
            asyncio.run(evaluator(_ev()))

        assert exc_info.value.evaluator_name == "ResponseQuality"
        assert exc_info.value.criteria == "Rate the response quality."
