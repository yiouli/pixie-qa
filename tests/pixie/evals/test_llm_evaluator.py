"""Tests for pixie.evals.llm_evaluator — create_llm_evaluator factory."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pixie.evals.evaluation import Evaluation
from pixie.evals.llm_evaluator import _LLMEvaluator, _parse_score, create_llm_evaluator
from pixie.storage.evaluable import UNSET, Evaluable


class TestCreateLLMEvaluator:
    """Tests for the create_llm_evaluator factory function."""

    def test_returns_llm_evaluator_instance(self) -> None:
        evaluator = create_llm_evaluator(
            name="TestEval",
            prompt_template="Rate: {eval_input} -> {eval_output}",
        )
        assert isinstance(evaluator, _LLMEvaluator)
        assert evaluator.name == "TestEval"

    def test_default_model(self) -> None:
        evaluator = create_llm_evaluator(
            name="TestEval",
            prompt_template="Rate: {eval_input}",
        )
        assert evaluator._model == "gpt-4o-mini"

    def test_custom_model(self) -> None:
        evaluator = create_llm_evaluator(
            name="TestEval",
            prompt_template="Rate: {eval_input}",
            model="gpt-4o",
        )
        assert evaluator._model == "gpt-4o"

    def test_custom_client(self) -> None:
        mock_client = MagicMock()
        evaluator = create_llm_evaluator(
            name="TestEval",
            prompt_template="Rate: {eval_input}",
            client=mock_client,
        )
        assert evaluator._client is mock_client


class TestLLMEvaluatorRendering:
    """Tests for prompt template rendering."""

    def test_renders_all_fields(self) -> None:
        evaluator = create_llm_evaluator(
            name="TestEval",
            prompt_template=(
                "Input: {eval_input}\nOutput: {eval_output}\n"
                "Expected: {expected_output}"
            ),
        )
        evaluable = Evaluable(
            eval_input="hello",
            eval_output="world",
            expected_output="world",
        )
        rendered = evaluator._render_prompt(evaluable)
        assert "Input: hello" in rendered
        assert "Output: world" in rendered
        assert "Expected: world" in rendered

    def test_renders_dict_input_as_json(self) -> None:
        evaluator = create_llm_evaluator(
            name="TestEval",
            prompt_template="Input: {eval_input}",
        )
        evaluable = Evaluable(
            eval_input={"user_message": "hi", "history": []},
            eval_output="response",
        )
        rendered = evaluator._render_prompt(evaluable)
        assert '"user_message": "hi"' in rendered

    def test_renders_unset_expected_output(self) -> None:
        evaluator = create_llm_evaluator(
            name="TestEval",
            prompt_template="Expected: {expected_output}",
        )
        evaluable = Evaluable(
            eval_input="hello",
            eval_output="world",
            expected_output=UNSET,
        )
        rendered = evaluator._render_prompt(evaluable)
        assert "(not provided)" in rendered

    def test_renders_none_input(self) -> None:
        evaluator = create_llm_evaluator(
            name="TestEval",
            prompt_template="Input: {eval_input}",
        )
        evaluable = Evaluable(eval_input=None, eval_output="out")
        rendered = evaluator._render_prompt(evaluable)
        assert "Input: " in rendered


class TestLLMEvaluatorCall:
    """Tests for the __call__ method with mocked OpenAI client."""

    @pytest.mark.asyncio()
    async def test_calls_openai_and_parses_score(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Score: 0.85\nGood response."
        mock_client.chat.completions.create.return_value = mock_response

        evaluator = create_llm_evaluator(
            name="TestEval",
            prompt_template="Rate: {eval_output}",
            client=mock_client,
        )
        evaluable = Evaluable(eval_input="q", eval_output="good answer")

        result = await evaluator(evaluable)

        assert isinstance(result, Evaluation)
        assert result.score == 0.85
        assert result.details["evaluator"] == "TestEval"
        mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio()
    async def test_handles_no_score_in_response(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "I cannot evaluate this."
        mock_client.chat.completions.create.return_value = mock_response

        evaluator = create_llm_evaluator(
            name="TestEval",
            prompt_template="Rate: {eval_output}",
            client=mock_client,
        )
        evaluable = Evaluable(eval_input="q", eval_output="answer")

        result = await evaluator(evaluable)
        assert result.score == 0.0
        assert "Failed to parse" in result.reasoning


class TestParseScore:
    """Tests for _parse_score helper."""

    def test_score_colon_pattern(self) -> None:
        score, reasoning = _parse_score("Score: 0.8\nGood work.")
        assert score == 0.8
        assert "Good work" in reasoning

    def test_score_equals_pattern(self) -> None:
        score, _ = _parse_score("Score=1.0")
        assert score == 1.0

    def test_fraction_pattern(self) -> None:
        score, _ = _parse_score("I rate this 0.7/1")
        assert score == 0.7

    def test_fraction_pattern_1_0(self) -> None:
        score, _ = _parse_score("0.5/1.0")
        assert score == 0.5

    def test_bare_float_on_line(self) -> None:
        score, _ = _parse_score("Analysis follows.\n0.9\nDone.")
        assert score == 0.9

    def test_no_parseable_score(self) -> None:
        score, reasoning = _parse_score("This is just text.")
        assert score == 0.0
        assert "Failed to parse" in reasoning

    def test_zero_score(self) -> None:
        score, _ = _parse_score("Score: 0.0")
        assert score == 0.0

    def test_one_score(self) -> None:
        score, _ = _parse_score("Score: 1.0")
        assert score == 1.0

    def test_integer_score(self) -> None:
        score, _ = _parse_score("Score: 1")
        assert score == 1.0
