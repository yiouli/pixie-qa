Module pixie.eval.scorers
=========================
Autoevals adapters — pre-made evaluators wrapping ``autoevals`` scorers.

This module provides :class:`AutoevalsAdapter`, which bridges the
autoevals ``Scorer`` interface to pixie's ``Evaluator`` protocol, and
a set of factory functions for common evaluation tasks.

Public API (all are also re-exported from ``pixie.eval``):

**Core adapter:**
    - :class:`AutoevalsAdapter` — generic wrapper for any autoevals ``Scorer``.

**Heuristic scorers (no LLM required):**
    - :func:`LevenshteinMatch` — edit-distance string similarity.
    - :func:`ExactMatch` — exact value comparison.
    - :func:`NumericDiff` — normalised numeric difference.
    - :func:`JSONDiff` — structural JSON comparison.
    - :func:`ValidJSON` — JSON syntax / schema validation.
    - :func:`ListContains` — overlap between two string lists.

**Embedding scorer:**
    - :func:`EmbeddingSimilarity` — cosine similarity via embeddings.

**LLM-as-judge scorers:**
    - :func:`Factuality`, :func:`ClosedQA`, :func:`Battle`,
      :func:`Humor`, :func:`Security`, :func:`Sql`,
      :func:`Summary`, :func:`Translation`, :func:`Possible`.

**Moderation:**
    - :func:`Moderation` — OpenAI content-moderation check.

**RAGAS metrics:**
    - :func:`ContextRelevancy`, :func:`Faithfulness`,
      :func:`AnswerRelevancy`, :func:`AnswerCorrectness`.

Evaluator Selection Guide
-------------------------

Choose evaluators based on the **output type** and eval criteria:

| Output type | Evaluator category | Examples |
| --- | --- | --- |
| Deterministic (labels, yes/no, fixed-format) | Heuristic: ``ExactMatch``, ``JSONDiff``, ``ValidJSON`` | Label classification, JSON extraction |
| Open-ended text with a reference answer | LLM-as-judge: ``Factuality``, ``ClosedQA``, ``AnswerCorrectness`` | Chatbot responses, QA, summaries |
| Text with expected context/grounding | RAG: ``Faithfulness``, ``ContextRelevancy`` | RAG pipelines |
| Text with style/format requirements | Custom via ``create_llm_evaluator`` | Voice-friendly responses, tone checks |
| Multi-aspect quality | Multiple evaluators combined | Factuality + relevance + tone |

Critical rules:

- For open-ended LLM text, **never** use ``ExactMatch`` — LLM outputs are
  non-deterministic.
- ``AnswerRelevancy`` is **RAG-only** — requires ``context`` in the trace.
  Returns 0.0 without it. For general relevance, use ``create_llm_evaluator``.
- Do NOT use comparison evaluators (``Factuality``, ``ClosedQA``,
  ``ExactMatch``) on items without ``expectation`` — they produce
  meaningless scores.

Functions
---------

`AnswerCorrectness(*, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
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

`AnswerRelevancy(*, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
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

`Battle(*, model: str | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Head-to-head comparison evaluator (LLM-as-judge).
    
    Uses an LLM to compare ``eval_output`` against ``expectation``
    and determine which is better given the instructions in ``eval_input``.
    
    **When to use**: A/B testing scenarios, comparing model outputs,
    or ranking alternative responses.
    
    **Requires ``expectation``**: Yes.
    
    Args:
        model: LLM model name.
        client: OpenAI client instance.

`ClosedQA(*, model: str | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
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

`ContextRelevancy(*, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Context relevancy evaluator (RAGAS).
    
    Judges whether the retrieved context is relevant to the query.
    Forwards ``eval_metadata["context"]`` to the underlying scorer.
    
    **When to use**: RAG pipelines — evaluating retrieval quality.
    
    **Requires ``expectation``**: Yes.
    **Requires ``eval_metadata["context"]``**: Yes (RAG pipelines only).
    
    Args:
        client: OpenAI client instance.

`EmbeddingSimilarity(*, prefix: str | None = None, model: str | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
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

`ExactMatch() ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Exact value comparison evaluator.
    
    Returns 1.0 if ``eval_output`` exactly equals ``expectation``,
    0.0 otherwise.
    
    **When to use**: Deterministic, structured outputs (classification labels,
    yes/no answers, fixed-format strings).  **Never** use for open-ended LLM
    text — LLM outputs are non-deterministic, so exact match will almost always
    fail.
    
    **Requires ``expectation``**: Yes.

`Factuality(*, model: str | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
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

`Faithfulness(*, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Faithfulness evaluator (RAGAS).
    
    Judges whether ``eval_output`` is faithful to (i.e. supported by)
    the provided context.  Forwards ``eval_metadata["context"]``.
    
    **When to use**: RAG pipelines — ensuring the answer doesn't
    hallucinate beyond what the retrieved context supports.
    
    **Requires ``expectation``**: No.
    **Requires ``eval_metadata["context"]``**: Yes (RAG pipelines only).
    
    Args:
        client: OpenAI client instance.

`Humor(*, model: str | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Humor quality evaluator (LLM-as-judge).
    
    Uses an LLM to judge the humor quality of ``eval_output`` against
    ``expectation``.
    
    **When to use**: Evaluating humor in creative writing, chatbot
    personality, or entertainment applications.
    
    **Requires ``expectation``**: Yes.
    
    Args:
        model: LLM model name.
        client: OpenAI client instance.

`JSONDiff(*, string_scorer: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Structural JSON comparison evaluator.
    
    Recursively compares two JSON structures and produces a similarity
    score.  Handles nested objects, arrays, and mixed types.
    
    **When to use**: Structured JSON outputs where field-level comparison
    is needed (e.g. extracted data, API response schemas, tool call arguments).
    
    **Requires ``expectation``**: Yes.
    
    Args:
        string_scorer: Optional pairwise scorer for string fields.

`LevenshteinMatch() ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Edit-distance string similarity evaluator.
    
    Computes a normalised Levenshtein distance between ``eval_output`` and
    ``expectation``.  Returns 1.0 for identical strings and decreasing
    scores as edit distance grows.
    
    **When to use**: Deterministic or near-deterministic outputs where small
    textual variations are acceptable (e.g. formatting differences, minor
    spelling).  Not suitable for open-ended LLM text — use an LLM-as-judge
    evaluator instead.
    
    **Requires ``expectation``**: Yes.

`ListContains(*, pairwise_scorer: Any = None, allow_extra_entities: bool = False) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   List overlap evaluator.
    
    Checks whether ``eval_output`` contains all items from
    ``expectation``.  Scores based on overlap ratio.
    
    **When to use**: Outputs that produce a list of items where completeness
    matters (e.g. extracted entities, search results, recommendations).
    
    **Requires ``expectation``**: Yes.
    
    Args:
        pairwise_scorer: Optional scorer for pairwise element comparison.
        allow_extra_entities: If True, extra items in output are not penalised.

`Moderation(*, threshold: float | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Content moderation evaluator.
    
    Uses the OpenAI moderation API to check ``eval_output`` for unsafe
    content (hate speech, violence, self-harm, etc.).
    
    **When to use**: Any application where output safety is a concern —
    chatbots, content generation, user-facing AI.
    
    **Requires ``expectation``**: No.
    
    Args:
        threshold: Custom flagging threshold.
        client: OpenAI client instance.

`NumericDiff() ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Normalised numeric difference evaluator.
    
    Computes a normalised numeric distance between ``eval_output`` and
    ``expectation``.  Returns 1.0 for identical numbers and decreasing
    scores as the difference grows.
    
    **When to use**: Numeric outputs where approximate equality is acceptable
    (e.g. price calculations, scores, measurements).
    
    **Requires ``expectation``**: Yes.

`Possible(*, model: str | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Feasibility / plausibility evaluator (LLM-as-judge).
    
    Uses an LLM to judge whether ``eval_output`` is a plausible or
    feasible response.
    
    **When to use**: General-purpose quality check when you want to
    verify outputs are reasonable without a specific reference answer.
    
    **Requires ``expectation``**: No.
    
    Args:
        model: LLM model name.
        client: OpenAI client instance.

`Security(*, model: str | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Security vulnerability evaluator (LLM-as-judge).
    
    Uses an LLM to check ``eval_output`` for security vulnerabilities
    based on the instructions in ``eval_input``.
    
    **When to use**: Code generation, SQL output, or any scenario
    where output must be checked for injection or vulnerability risks.
    
    **Requires ``expectation``**: No.
    
    Args:
        model: LLM model name.
        client: OpenAI client instance.

`Sql(*, model: str | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   SQL equivalence evaluator (LLM-as-judge).
    
    Uses an LLM to judge whether ``eval_output`` SQL is semantically
    equivalent to ``expectation`` SQL.
    
    **When to use**: Text-to-SQL applications where the generated SQL
    should be functionally equivalent to a reference query.
    
    **Requires ``expectation``**: Yes.
    
    Args:
        model: LLM model name.
        client: OpenAI client instance.

`Summary(*, model: str | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Summarisation quality evaluator (LLM-as-judge).
    
    Uses an LLM to judge the quality of ``eval_output`` as a summary
    compared to the reference summary in ``expectation``.
    
    **When to use**: Summarisation tasks where the output must capture
    key information from the source material.
    
    **Requires ``expectation``**: Yes.
    
    Args:
        model: LLM model name.
        client: OpenAI client instance.

`Translation(*, language: str | None = None, model: str | None = None, client: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   Translation quality evaluator (LLM-as-judge).
    
    Uses an LLM to judge the translation quality of ``eval_output``
    compared to ``expectation`` in the target language.
    
    **When to use**: Machine translation or multilingual output scenarios.
    
    **Requires ``expectation``**: Yes.
    
    Args:
        language: Target language (e.g. ``"Spanish"``).
        model: LLM model name.
        client: OpenAI client instance.

`ValidJSON(*, schema: Any = None) ‑> pixie.eval.scorers.AutoevalsAdapter`
:   JSON syntax and schema validation evaluator.
    
    Returns 1.0 if ``eval_output`` is valid JSON (and optionally matches
    the provided schema), 0.0 otherwise.
    
    **When to use**: Outputs that must be valid JSON — optionally conforming
    to a specific schema (e.g. tool call responses, structured extraction).
    
    **Requires ``expectation``**: No.
    
    Args:
        schema: Optional JSON Schema to validate against.

`_score_to_evaluation(score: _Score) ‑> pixie.eval.evaluation.Evaluation`
:   Convert an autoevals ``Score`` to a pixie ``Evaluation``.
    
    Mapping rules:
        - ``score.score``  → ``evaluation.score`` (``None`` becomes ``0.0``).
        - ``score.metadata["rationale"]`` → ``evaluation.reasoning`` when
          present and non-empty; otherwise a default string is generated.
        - The full ``score.metadata`` dict is forwarded to
          ``evaluation.details`` with an extra ``scorer_name`` key.

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