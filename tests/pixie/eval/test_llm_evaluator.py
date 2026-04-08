"""Tests for pixie.evals.llm_evaluator — create_llm_evaluator factory."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import JsonValue

from pixie.eval.evaluable import UNSET, Evaluable, NamedData, _Unset
from pixie.eval.evaluation import Evaluation
from pixie.eval.llm_evaluator import _LLMEvaluator, _parse_score, create_llm_evaluator


def _nd(name: str, value: JsonValue) -> NamedData:
    return NamedData(name=name, value=value)


def _ev(
    inp: JsonValue = None,
    out: JsonValue = None,
    expectation: JsonValue | _Unset = UNSET,
    eval_metadata: dict[str, JsonValue] | None = None,
    description: str | None = None,
) -> Evaluable:
    return Evaluable(
        eval_input=[_nd("input", inp)],
        eval_output=[_nd("output", out)],
        expectation=expectation,
        eval_metadata=eval_metadata,
        description=description,
    )


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
                "Input: {eval_input}\nOutput: {eval_output}\nExpected: {expectation}"
            ),
        )
        evaluable = _ev(inp="hello", out="world", expectation="world")
        rendered = evaluator._render_prompt(evaluable)
        assert "Input: hello" in rendered
        assert "Output: world" in rendered
        assert "Expected: world" in rendered

    def test_renders_dict_input_as_json(self) -> None:
        evaluator = create_llm_evaluator(
            name="TestEval",
            prompt_template="Input: {eval_input}",
        )
        evaluable = _ev(
            inp={"user_message": "hi", "history": []},
            out="response",
        )
        rendered = evaluator._render_prompt(evaluable)
        assert '"user_message": "hi"' in rendered

    def test_renders_unset_expected_output(self) -> None:
        evaluator = create_llm_evaluator(
            name="TestEval",
            prompt_template="Expected: {expectation}",
        )
        evaluable = _ev(
            inp="hello",
            out="world",
            expectation=UNSET,
        )
        rendered = evaluator._render_prompt(evaluable)
        assert "(not provided)" in rendered

    def test_renders_none_input(self) -> None:
        evaluator = create_llm_evaluator(
            name="TestEval",
            prompt_template="Input: {eval_input}",
        )
        evaluable = _ev(inp=None, out="out")
        rendered = evaluator._render_prompt(evaluable)
        assert "Input: " in rendered

    def test_renders_multiple_eval_input_items(self) -> None:
        evaluator = create_llm_evaluator(
            name="TestEval",
            prompt_template="Input: {eval_input}",
        )
        evaluable = Evaluable(
            eval_input=[
                _nd("question", "What is 2+2?"),
                _nd("context", "Math class"),
            ],
            eval_output=[_nd("answer", "4")],
        )
        rendered = evaluator._render_prompt(evaluable)
        assert '"question": "What is 2+2?"' in rendered
        assert '"context": "Math class"' in rendered

    def test_renders_multiple_eval_output_items(self) -> None:
        evaluator = create_llm_evaluator(
            name="TestEval",
            prompt_template="Output: {eval_output}",
        )
        evaluable = Evaluable(
            eval_input=[_nd("q", "hi")],
            eval_output=[
                _nd("response", "Hello!"),
                _nd("function_called", "greet"),
                _nd("call_ended", True),
            ],
        )
        rendered = evaluator._render_prompt(evaluable)
        assert '"response": "Hello!"' in rendered
        assert '"function_called": "greet"' in rendered
        assert '"call_ended": true' in rendered

    def test_single_item_renders_value_directly(self) -> None:
        """Single-item lists render the bare value (backwards compatible)."""
        evaluator = create_llm_evaluator(
            name="TestEval",
            prompt_template="Output: {eval_output}",
        )
        evaluable = _ev(inp="q", out="simple answer")
        rendered = evaluator._render_prompt(evaluable)
        assert "Output: simple answer" in rendered
        # Should NOT be wrapped in a JSON dict
        assert '"output"' not in rendered


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
        evaluable = _ev(inp="q", out="good answer")

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
        evaluable = _ev(inp="q", out="answer")

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


class TestTemplateValidation:
    """Tests for template validation in create_llm_evaluator."""

    def test_rejects_nested_eval_input_access(self) -> None:
        with pytest.raises(ValueError, match="Nested field access"):
            create_llm_evaluator(
                name="Bad",
                prompt_template="User said: {eval_input[user_message]}",
            )

    def test_rejects_nested_eval_output_access(self) -> None:
        with pytest.raises(ValueError, match="Nested field access"):
            create_llm_evaluator(
                name="Bad",
                prompt_template="Response: {eval_output[response]}",
            )

    def test_rejects_nested_expectation_access(self) -> None:
        with pytest.raises(ValueError, match="Nested field access"):
            create_llm_evaluator(
                name="Bad",
                prompt_template="Expected: {expectation[key]}",
            )

    def test_accepts_valid_template(self) -> None:
        evaluator = create_llm_evaluator(
            name="Good",
            prompt_template="Input: {eval_input}\nOutput: {eval_output}",
        )
        assert evaluator.name == "Good"


class TestScoreFormatReminder:
    """Tests that rendered prompts include score format reminder."""

    def test_render_appends_score_reminder(self) -> None:
        evaluator = create_llm_evaluator(
            name="TestEval",
            prompt_template="Rate: {eval_output}",
        )
        evaluable = _ev(inp="q", out="answer")
        rendered = evaluator._render_prompt(evaluable)
        assert "Respond with 'Score: X.X'" in rendered
