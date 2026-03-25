"""Factory for custom LLM-as-judge evaluators from prompt templates.

Usage::

    from pixie import create_llm_evaluator

    concise_voice_style = create_llm_evaluator(
        name="ConciseVoiceStyle",
        prompt_template=\"\"\"
        You are evaluating whether a voice agent response is concise and
        phone-friendly.

        User said: {eval_input}
        Agent responded: {eval_output}
        Expected behavior: {expected_output}

        Score 1.0 if the response is concise (under 3 sentences), directly
        addresses the question, and uses conversational language suitable for
        a phone call. Score 0.0 if it's verbose, off-topic, or uses
        written-style formatting.
        \"\"\",
    )
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import OpenAI

from pixie.evals.evaluation import Evaluation
from pixie.storage.evaluable import Evaluable, _Unset
from pixie.storage.tree import ObservationNode

logger = logging.getLogger(__name__)

# Default model for LLM-as-judge calls
_DEFAULT_MODEL = "gpt-4o-mini"


def _value_to_str(value: Any) -> str:
    """Convert an eval value to a string for template substitution."""
    if value is None:
        return ""
    if isinstance(value, _Unset):
        return "(not provided)"
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return str(value)


def _parse_score(text: str) -> tuple[float, str]:
    """Extract a 0-1 score and reasoning from LLM response text.

    Looks for patterns like "Score: 0.8", "score: 1.0", "0.7/1.0", or
    a bare float on its own line. Returns (score, reasoning).
    """
    # Try "Score: X" pattern first
    match = re.search(r"[Ss]core\s*[:=]\s*([01](?:\.\d+)?)", text)
    if match:
        score = float(match.group(1))
        return min(max(score, 0.0), 1.0), text.strip()

    # Try "X/1" or "X/1.0" pattern
    match = re.search(r"([01](?:\.\d+)?)\s*/\s*1(?:\.0)?", text)
    if match:
        score = float(match.group(1))
        return min(max(score, 0.0), 1.0), text.strip()

    # Try bare float on a line
    match = re.search(r"^([01](?:\.\d+)?)\s*$", text, re.MULTILINE)
    if match:
        score = float(match.group(1))
        return min(max(score, 0.0), 1.0), text.strip()

    # Fallback: couldn't parse score
    logger.warning("Could not parse score from LLM response: %s", text[:200])
    return 0.0, f"Failed to parse score. Raw response: {text.strip()}"


class _LLMEvaluator:
    """Evaluator that uses an LLM to judge quality via a prompt template."""

    def __init__(
        self,
        name: str,
        prompt_template: str,
        model: str,
        client: Any | None,
    ) -> None:
        self._name = name
        self._prompt_template = prompt_template
        self._model = model
        self._client = client

    @property
    def name(self) -> str:
        """Return the evaluator's display name."""
        return self._name

    def _get_client(self) -> Any:
        """Get or create the OpenAI client."""
        if self._client is not None:
            return self._client

        return OpenAI()

    def _render_prompt(self, evaluable: Evaluable) -> str:
        """Fill in the template with evaluable fields."""
        expected = evaluable.expected_output
        return self._prompt_template.format(
            eval_input=_value_to_str(evaluable.eval_input),
            eval_output=_value_to_str(evaluable.eval_output),
            expected_output=_value_to_str(expected),
        )

    async def __call__(
        self,
        evaluable: Evaluable,
        *,
        trace: list[ObservationNode] | None = None,
    ) -> Evaluation:
        """Run the LLM judge and parse the score."""
        import asyncio

        prompt = self._render_prompt(evaluable)
        client = self._get_client()

        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an evaluation judge. Score the following on "
                        "a scale of 0.0 to 1.0. Always include 'Score: X.X' "
                        "in your response, followed by your reasoning."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )

        text = response.choices[0].message.content or ""
        score, reasoning = _parse_score(text)

        return Evaluation(
            score=score,
            reasoning=reasoning,
            details={"evaluator": self._name, "model": self._model},
        )


def create_llm_evaluator(
    name: str,
    prompt_template: str,
    *,
    model: str = _DEFAULT_MODEL,
    client: Any | None = None,
) -> _LLMEvaluator:
    """Create a custom LLM-as-judge evaluator from a prompt template.

    The template may reference these variables (populated from the
    :class:`~pixie.storage.evaluable.Evaluable` fields):

    - ``{eval_input}`` — the evaluable's input
    - ``{eval_output}`` — the evaluable's output
    - ``{expected_output}`` — the evaluable's expected output

    Args:
        name: Display name for the evaluator (shown in scorecard).
        prompt_template: A string template with ``{eval_input}``,
            ``{eval_output}``, and/or ``{expected_output}`` placeholders.
        model: OpenAI model name (default: ``gpt-4o-mini``).
        client: Optional pre-configured OpenAI client instance.

    Returns:
        An evaluator callable satisfying the ``Evaluator`` protocol.
    """
    return _LLMEvaluator(
        name=name,
        prompt_template=prompt_template,
        model=model,
        client=client,
    )
