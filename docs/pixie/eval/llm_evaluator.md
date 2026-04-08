Module pixie.eval.llm_evaluator
===============================
Factory for custom LLM-as-judge evaluators from prompt templates.

Usage::

    from pixie import create_llm_evaluator

    concise_voice_style = create_llm_evaluator(
        name="ConciseVoiceStyle",
        prompt_template="""
        You are evaluating whether a voice agent response is concise and
        phone-friendly.

        User said: {eval_input}
        Agent responded: {eval_output}
        Expected behavior: {expectation}

        Score 1.0 if the response is concise (under 3 sentences), directly
        addresses the question, and uses conversational language suitable for
        a phone call. Score 0.0 if it's verbose, off-topic, or uses
        written-style formatting.
        """,
    )

Functions
---------

`def create_llm_evaluator(name: str, prompt_template: str, *, model: str = 'gpt-4o-mini', client: Any | None = None) ‑> pixie.eval.llm_evaluator._LLMEvaluator`
:   Create a custom LLM-as-judge evaluator from a prompt template.
    
    The template may reference these variables (populated from the
    :class:`~pixie.eval.evaluable.Evaluable` fields):
    
    - ``{eval_input}`` — the evaluable's input data. When there is a
      single ``eval_input`` item, this expands to that item's value.
      When there are multiple items, it expands to a JSON dict mapping
      each item's ``name`` to its ``value``.
    - ``{eval_output}`` — the evaluable's output data (same rule as
      ``eval_input``).
    - ``{expectation}`` — the evaluable's expected output.
    
    Args:
        name: Display name for the evaluator (shown in scorecard).
        prompt_template: A string template with ``{eval_input}``,
            ``{eval_output}``, and/or ``{expectation}`` placeholders.
        model: OpenAI model name (default: ``gpt-4o-mini``).
        client: Optional pre-configured OpenAI client instance.
    
    Returns:
        An evaluator callable satisfying the ``Evaluator`` protocol.
    
    Raises:
        ValueError: If the template uses nested field access like
            ``{eval_input[key]}`` (only top-level placeholders are supported).