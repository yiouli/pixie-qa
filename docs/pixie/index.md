Module pixie
============
pixie — automated quality assurance for AI applications.

Re-exports the full public API so users can ``from pixie import ...``
for every commonly used symbol without needing submodule paths.

Sub-modules
-----------
* pixie.cli
* pixie.config
* pixie.eval
* pixie.harness
* pixie.instrumentation
* pixie.web

Functions
---------

`def AnswerCorrectness(*, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Answer correctness evaluator (RAGAS).
    
    Judges whether ``eval_output`` is correct compared to
    ``expectation``, combining factual similarity and semantic
    similarity.
    
    **When to use**: QA scenarios in RAG pipelines where you have a
    reference answer and want a comprehensive correctness score.
    
    **Requires ``expectation``**: Yes.
    **Requires ``eval_metadata["context"]``**: Optional (improves accuracy).
    
    Args:
        client: OpenAI client instance.

`def AnswerRelevancy(*, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Answer relevancy evaluator (RAGAS).
    
    Judges whether ``eval_output`` directly addresses the question in
    ``eval_input``.
    
    **When to use**: RAG pipelines only — requires ``context`` in the
    trace.  Returns 0.0 without it.  For general (non-RAG) response
    relevance, use ``create_llm_evaluator`` with a custom prompt instead.
    
    **Requires ``expectation``**: No.
    **Requires ``eval_metadata["context"]``**: Yes — **RAG pipelines only**.
    
    Args:
        client: OpenAI client instance.

`def Battle(*, model: str | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Head-to-head comparison evaluator (LLM-as-judge).
    
    Uses an LLM to compare ``eval_output`` against ``expectation``
    and determine which is better given the instructions in ``eval_input``.
    
    **When to use**: A/B testing scenarios, comparing model outputs,
    or ranking alternative responses.
    
    **Requires ``expectation``**: Yes.
    
    Args:
        model: LLM model name.
        client: OpenAI client instance.

`def ClosedQA(*, model: str | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Closed-book question-answering evaluator (LLM-as-judge).
    
    Uses an LLM to judge whether ``eval_output`` correctly answers the
    question in ``eval_input`` compared to ``expectation``.  Optionally
    forwards ``eval_metadata["criteria"]`` for custom grading criteria.
    
    **When to use**: QA scenarios where the answer should match a reference —
    e.g. customer support answers, knowledge-base queries.
    
    **Requires ``expectation``**: Yes — do NOT use on items without
    ``expectation``; produces meaningless scores.
    
    Args:
        model: LLM model name.
        client: OpenAI client instance.

`def ContextRelevancy(*, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Context relevancy evaluator (RAGAS).
    
    Judges whether the retrieved context is relevant to the query.
    Forwards ``eval_metadata["context"]`` to the underlying scorer.
    
    **When to use**: RAG pipelines — evaluating retrieval quality.
    
    **Requires ``expectation``**: Yes.
    **Requires ``eval_metadata["context"]``**: Yes (RAG pipelines only).
    
    Args:
        client: OpenAI client instance.

`def EmbeddingSimilarity(*, prefix: str | None = None, model: str | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Embedding-based semantic similarity evaluator.
    
    Computes cosine similarity between embedding vectors of ``eval_output``
    and ``expectation``.
    
    **When to use**: Comparing semantic meaning of two texts when exact
    wording doesn't matter.  More robust than Levenshtein for paraphrased
    content but less nuanced than LLM-as-judge evaluators.
    
    **Requires ``expectation``**: Yes.
    
    Args:
        prefix: Optional text to prepend for domain context.
        model: Embedding model name.
        client: OpenAI client instance.

`def ExactMatch() ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Exact value comparison evaluator.
    
    Returns 1.0 if ``eval_output`` exactly equals ``expectation``,
    0.0 otherwise.
    
    **When to use**: Deterministic, structured outputs (classification labels,
    yes/no answers, fixed-format strings).  **Never** use for open-ended LLM
    text — LLM outputs are non-deterministic, so exact match will almost always
    fail.
    
    **Requires ``expectation``**: Yes.

`def Factuality(*, model: str | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Factual accuracy evaluator (LLM-as-judge).
    
    Uses an LLM to judge whether ``eval_output`` is factually consistent
    with ``expectation`` given the ``eval_input`` context.
    
    **When to use**: Open-ended text where factual correctness matters
    (chatbot responses, QA answers, summaries).  Preferred over
    ``ExactMatch`` for LLM-generated text.
    
    **Requires ``expectation``**: Yes — do NOT use on items without
    ``expectation``; produces meaningless scores.
    
    Args:
        model: LLM model name.
        client: OpenAI client instance.

`def Faithfulness(*, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Faithfulness evaluator (RAGAS).
    
    Judges whether ``eval_output`` is faithful to (i.e. supported by)
    the provided context.  Forwards ``eval_metadata["context"]``.
    
    **When to use**: RAG pipelines — ensuring the answer doesn't
    hallucinate beyond what the retrieved context supports.
    
    **Requires ``expectation``**: No.
    **Requires ``eval_metadata["context"]``**: Yes (RAG pipelines only).
    
    Args:
        client: OpenAI client instance.

`def Humor(*, model: str | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Humor quality evaluator (LLM-as-judge).
    
    Uses an LLM to judge the humor quality of ``eval_output`` against
    ``expectation``.
    
    **When to use**: Evaluating humor in creative writing, chatbot
    personality, or entertainment applications.
    
    **Requires ``expectation``**: Yes.
    
    Args:
        model: LLM model name.
        client: OpenAI client instance.

`def JSONDiff(*, string_scorer: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Structural JSON comparison evaluator.
    
    Recursively compares two JSON structures and produces a similarity
    score.  Handles nested objects, arrays, and mixed types.
    
    **When to use**: Structured JSON outputs where field-level comparison
    is needed (e.g. extracted data, API response schemas, tool call arguments).
    
    **Requires ``expectation``**: Yes.
    
    Args:
        string_scorer: Optional pairwise scorer for string fields.

`def LevenshteinMatch() ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Edit-distance string similarity evaluator.
    
    Computes a normalised Levenshtein distance between ``eval_output`` and
    ``expectation``.  Returns 1.0 for identical strings and decreasing
    scores as edit distance grows.
    
    **When to use**: Deterministic or near-deterministic outputs where small
    textual variations are acceptable (e.g. formatting differences, minor
    spelling).  Not suitable for open-ended LLM text — use an LLM-as-judge
    evaluator instead.
    
    **Requires ``expectation``**: Yes.

`def ListContains(*, pairwise_scorer: Any = None, allow_extra_entities: bool = False) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   List overlap evaluator.
    
    Checks whether ``eval_output`` contains all items from
    ``expectation``.  Scores based on overlap ratio.
    
    **When to use**: Outputs that produce a list of items where completeness
    matters (e.g. extracted entities, search results, recommendations).
    
    **Requires ``expectation``**: Yes.
    
    Args:
        pairwise_scorer: Optional scorer for pairwise element comparison.
        allow_extra_entities: If True, extra items in output are not penalised.

`def Moderation(*, threshold: float | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Content moderation evaluator.
    
    Uses the OpenAI moderation API to check ``eval_output`` for unsafe
    content (hate speech, violence, self-harm, etc.).
    
    **When to use**: Any application where output safety is a concern —
    chatbots, content generation, user-facing AI.
    
    **Requires ``expectation``**: No.
    
    Args:
        threshold: Custom flagging threshold.
        client: OpenAI client instance.

`def NumericDiff() ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Normalised numeric difference evaluator.
    
    Computes a normalised numeric distance between ``eval_output`` and
    ``expectation``.  Returns 1.0 for identical numbers and decreasing
    scores as the difference grows.
    
    **When to use**: Numeric outputs where approximate equality is acceptable
    (e.g. price calculations, scores, measurements).
    
    **Requires ``expectation``**: Yes.

`def Possible(*, model: str | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Feasibility / plausibility evaluator (LLM-as-judge).
    
    Uses an LLM to judge whether ``eval_output`` is a plausible or
    feasible response.
    
    **When to use**: General-purpose quality check when you want to
    verify outputs are reasonable without a specific reference answer.
    
    **Requires ``expectation``**: No.
    
    Args:
        model: LLM model name.
        client: OpenAI client instance.

`def Security(*, model: str | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Security vulnerability evaluator (LLM-as-judge).
    
    Uses an LLM to check ``eval_output`` for security vulnerabilities
    based on the instructions in ``eval_input``.
    
    **When to use**: Code generation, SQL output, or any scenario
    where output must be checked for injection or vulnerability risks.
    
    **Requires ``expectation``**: No.
    
    Args:
        model: LLM model name.
        client: OpenAI client instance.

`def Sql(*, model: str | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   SQL equivalence evaluator (LLM-as-judge).
    
    Uses an LLM to judge whether ``eval_output`` SQL is semantically
    equivalent to ``expectation`` SQL.
    
    **When to use**: Text-to-SQL applications where the generated SQL
    should be functionally equivalent to a reference query.
    
    **Requires ``expectation``**: Yes.
    
    Args:
        model: LLM model name.
        client: OpenAI client instance.

`def Summary(*, model: str | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Summarisation quality evaluator (LLM-as-judge).
    
    Uses an LLM to judge the quality of ``eval_output`` as a summary
    compared to the reference summary in ``expectation``.
    
    **When to use**: Summarisation tasks where the output must capture
    key information from the source material.
    
    **Requires ``expectation``**: Yes.
    
    Args:
        model: LLM model name.
        client: OpenAI client instance.

`def Translation(*, language: str | None = None, model: str | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Translation quality evaluator (LLM-as-judge).
    
    Uses an LLM to judge the translation quality of ``eval_output``
    compared to ``expectation`` in the target language.
    
    **When to use**: Machine translation or multilingual output scenarios.
    
    **Requires ``expectation``**: Yes.
    
    Args:
        language: Target language (e.g. ``"Spanish"``).
        model: LLM model name.
        client: OpenAI client instance.

`def ValidJSON(*, schema: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   JSON syntax and schema validation evaluator.
    
    Returns 1.0 if ``eval_output`` is valid JSON (and optionally matches
    the provided schema), 0.0 otherwise.
    
    **When to use**: Outputs that must be valid JSON — optionally conforming
    to a specific schema (e.g. tool call responses, structured extraction).
    
    **Requires ``expectation``**: No.
    
    Args:
        schema: Optional JSON Schema to validate against.

`def add_handler(handler: InstrumentationHandler) ‑> None`
:   Register *handler* to receive span notifications.
    
    Must be called after :func:`enable_llm_tracing`.  Multiple handlers can
    be registered; each receives every span.

`def create_llm_evaluator(name: str, prompt_template: str, *, model: str = 'gpt-4o-mini', client: Any | None = None) ‑> pixie.eval.llm_evaluator._LLMEvaluator`
:   Create a custom LLM-as-judge evaluator from a prompt template.
    
    The template may reference these variables (populated from the
    :class:`~pixie.eval.evaluable.Evaluable` fields):
    
    - ``{eval_input}`` — the evaluable's input
    - ``{eval_output}`` — the evaluable's output
    - ``{expectation}`` — the evaluable's expected output
    
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

`def enable_llm_tracing(*, capture_content: bool = True, queue_size: int = 1000) ‑> None`
:   Initialize the LLM tracing sub-system.
    
    Sets up the OpenTelemetry ``TracerProvider``, span processor, delivery
    queue, and activates auto-instrumentors for known LLM providers.
    Truly idempotent — calling ``enable_llm_tracing()`` a second time is
    a no-op.
    
    Handler registration is done separately via :func:`add_handler`.

`async def evaluate(evaluator: Callable[..., Any], evaluable: Evaluable) ‑> pixie.eval.evaluation.Evaluation`
:   Run a single evaluator against a single evaluable.
    
    Behavior:
        1. If *evaluator* is sync, wrap via ``asyncio.to_thread``.
        2. Call evaluator with *evaluable*.
        3. Clamp returned ``score`` to [0.0, 1.0].
        4. If evaluator raises, the exception propagates to the caller.
           Evaluator errors (missing API keys, network failures, etc.)
           are never silently converted to a zero score.
    
    Args:
        evaluator: An evaluator callable (sync or async).
        evaluable: The data to evaluate.
    
    Raises:
        Exception: Any exception raised by the evaluator propagates
            unchanged so callers see clear, actionable errors.

`def flush(timeout_seconds: float = 5.0) ‑> bool`
:   Flush the delivery queue, blocking until all items are processed.

`def remove_handler(handler: InstrumentationHandler) ‑> None`
:   Unregister a previously registered *handler*.
    
    Raises ``ValueError`` if *handler* was not registered.

`def wrap(data: T, *, purpose: Purpose, name: str, description: str | None = None) ‑> ~T`
:   Observe *data* at a named wrap point with a specified purpose.

Classes
-------

`AutoevalsAdapter(scorer: _Scorer, *, expected: Any = <object object>, expected_key: str = 'expected', input_key: str | None = 'input', extra_metadata_keys: tuple[str, ...] = (), **scorer_kwargs: Any)`
:   Wrap an autoevals ``Scorer`` to satisfy the pixie ``Evaluator`` protocol.
    
    The adapter translates between two interfaces:
    
    * **pixie** — evaluator receives :class:`~pixie.eval.evaluable.Evaluable`
      (``eval_input``, ``eval_output``, ``eval_metadata``) and returns
      :class:`~pixie.eval.evaluation.Evaluation`.
    * **autoevals** — scorer receives ``output``, ``expected``, ``**kwargs``
      and returns :class:`autoevals.score.Score`.
    
    Args:
        scorer: The autoevals ``Scorer`` instance to delegate to.
        expected: Fixed expected value. If not provided, the adapter reads
            ``evaluable.eval_metadata[expected_key]`` at call time.
        expected_key: Metadata key to read ``expected`` from (default
            ``"expected"``).
        input_key: If not ``None``, ``evaluable.eval_input`` is forwarded as
            this kwarg to the scorer (default ``"input"``). Set to ``None``
            to skip.
        extra_metadata_keys: Additional metadata keys to forward as kwargs.
        **scorer_kwargs: Extra fixed kwargs passed to every ``eval_async``
            call.

    ### Instance variables

    `name: str`
    :   Return the underlying scorer's display name.

`Evaluable(**data: Any)`
:   TestCase plus actual output — the full data carrier for evaluators.
    
    Inherits all ``TestCase`` fields and adds ``eval_output``.
    
    Attributes:
        eval_output: Named output data items from the observed operation
            (non-empty).
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pixie.eval.evaluable.TestCase
    * pydantic.main.BaseModel

    ### Class variables

    `eval_output: list[pixie.eval.evaluable.NamedData]`
    :

    `model_config`
    :

`Evaluation(score: float, reasoning: str, details: dict[str, Any] = <factory>)`
:   The result of a single evaluator applied to a single test case.
    
    Attributes:
        score: Evaluation score between 0.0 and 1.0.
        reasoning: Human-readable explanation (required).
        details: Arbitrary JSON-serializable metadata.

    ### Instance variables

    `details: dict[str, typing.Any]`
    :

    `reasoning: str`
    :

    `score: float`
    :

`Evaluator(*args, **kwargs)`
:   Protocol for evaluation callables.
    
    An evaluator is any callable (async or sync) matching this signature.
    Plain async functions, class instances with ``__call__``, or closures
    all satisfy this protocol. Sync evaluators are automatically wrapped
    via ``asyncio.to_thread`` at call time.

    ### Ancestors (in MRO)

    * typing.Protocol
    * typing.Generic

`TestCase(**data: Any)`
:   Scenario definition without actual output.
    
    Defines the input, expectation, and metadata for a test case.
    Does not include the actual output — use ``Evaluable`` for that.
    
    Attributes:
        eval_input: Named input data items (non-empty).
        expectation: Expected/reference output for evaluation.
            Defaults to ``UNSET`` (not provided). May be explicitly
            set to ``None`` to indicate "no expectation".
        eval_metadata: Supplementary metadata (``None`` when absent).
        description: Human-readable description.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel

    ### Descendants

    * pixie.eval.evaluable.Evaluable

    ### Class variables

    `description: str | None`
    :

    `eval_input: list[pixie.eval.evaluable.NamedData]`
    :

    `eval_metadata: dict[str, JsonValue] | None`
    :

    `expectation: JsonValue | pixie.eval.evaluable._Unset`
    :

    `model_config`
    :

`WrappedData(**data: Any)`
:   A single ``wrap()`` observation record.
    
    Used in three contexts:
    
    1. **Trace files** — written to JSONL by the trace writer.
    2. **Dataset ``eval_input``** — each dataset item stores its input
       as ``list[WrappedData]`` (JSON-serialized).
    3. **In-memory emission** — created by ``wrap()`` before dispatching.
    
    Attributes:
        type: Always ``"wrap"`` for wrap events.
        name: The wrap point name (matches ``wrap(name=...)``).
        purpose: One of `"input"``, ``"output"``, ``"state"``.
        data: The observed data value (stored as JSON-compatible value).
        description: Optional human-readable description.
        trace_id: OTel trace ID (if available).
        span_id: OTel span ID (if available).
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel

    ### Class variables

    `data: JsonValue`
    :

    `description: str | None`
    :

    `model_config`
    :

    `name: str`
    :

    `purpose: Literal['input', 'output', 'state']`
    :

    `span_id: str | None`
    :

    `trace_id: str | None`
    :

    `type: str`
    :