# Testing API Reference

> Auto-generated from pixie source code docstrings.
> Do not edit by hand — run `uv run python scripts/generate_skill_docs.py`.

pixie.evals — evaluation harness for LLM applications.

Public API:
    - ``Evaluation`` — result dataclass for a single evaluator run
    - ``Evaluator`` — protocol for evaluation callables
    - ``evaluate`` — run one evaluator against one evaluable
    - ``run_and_evaluate`` — evaluate spans from a MemoryTraceHandler
    - ``assert_pass`` — batch evaluation with pass/fail criteria
    - ``assert_dataset_pass`` — load a dataset and run assert_pass
    - ``EvalAssertionError`` — raised when assert_pass fails
    - ``capture_traces`` — context manager for in-memory trace capture
    - ``MemoryTraceHandler`` — InstrumentationHandler that collects spans
    - ``ScoreThreshold`` — configurable pass criteria
    - ``last_llm_call`` / ``root`` — trace-to-evaluable helpers
    - ``DatasetEntryResult`` — evaluation results for a single dataset entry
    - ``DatasetScorecard`` — per-dataset scorecard with non-uniform evaluators
    - ``generate_dataset_scorecard_html`` — render a scorecard as HTML
    - ``save_dataset_scorecard`` — write scorecard HTML to disk

Pre-made evaluators (autoevals adapters):
    - ``AutoevalsAdapter`` — generic wrapper for any autoevals ``Scorer``
    - ``LevenshteinMatch`` — edit-distance string similarity
    - ``ExactMatch`` — exact value comparison
    - ``NumericDiff`` — normalised numeric difference
    - ``JSONDiff`` — structural JSON comparison
    - ``ValidJSON`` — JSON syntax / schema validation
    - ``ListContains`` — list overlap
    - ``EmbeddingSimilarity`` — embedding cosine similarity
    - ``Factuality`` — LLM factual accuracy check
    - ``ClosedQA`` — closed-book QA evaluation
    - ``Battle`` — head-to-head comparison
    - ``Humor`` — humor detection
    - ``Security`` — security vulnerability check
    - ``Sql`` — SQL equivalence
    - ``Summary`` — summarisation quality
    - ``Translation`` — translation quality
    - ``Possible`` — feasibility check
    - ``Moderation`` — content moderation
    - ``ContextRelevancy`` — RAGAS context relevancy
    - ``Faithfulness`` — RAGAS faithfulness
    - ``AnswerRelevancy`` — RAGAS answer relevancy
    - ``AnswerCorrectness`` — RAGAS answer correctness

Dataset JSON Format
-------------------

::

    {
      "name": "customer-faq",
      "runnable": "pixie_qa/scripts/run_app.py:run_app",
      "evaluators": ["Factuality"],
      "items": [
        {
          "description": "Basic greeting",
          "eval_input": {"question": "Hello"},
          "expected_output": "Hi, how can I help?"
        }
      ]
    }

Fields:

- ``runnable`` (required): ``filepath:callable_name`` reference to the function
  that produces ``eval_output`` from ``eval_input``.
- ``evaluators`` (optional): Dataset-level default evaluator names. Applied to
  items without row-level evaluators.
- ``items[].evaluators`` (optional): Row-level evaluator names. Use ``"..."`` to
  include dataset defaults.
- ``items[].description`` (required): Human-readable label for the test case.
- ``items[].eval_input`` (required): Input passed to the runnable.
- ``items[].expected_output`` (optional): Reference value for comparison-based
  evaluators.
- ``items[].eval_output`` (optional): Pre-computed output (skips runnable
  execution).

Evaluator Name Resolution
--------------------------

In dataset JSON, evaluator names are resolved as follows:

- **Built-in names** (bare names like ``"Factuality"``, ``"ExactMatch"``) are
  resolved to ``pixie.{Name}`` automatically.
- **Custom evaluators** use ``filepath:callable_name`` format
  (e.g. ``"pixie_qa/evaluators.py:my_evaluator"``).
- Custom evaluator references point to module-level callables — classes
  (instantiated automatically), factory functions (called if zero-arg),
  evaluator functions (used as-is), or pre-instantiated callables (e.g.
  ``create_llm_evaluator`` results — used as-is).

CLI Commands
------------

| Command | Description |
| --- | --- |
| ``pixie test [path] [-v] [--no-open]`` | Run eval tests on dataset files |
| ``pixie dataset create <name>`` | Create a new empty dataset |
| ``pixie dataset list`` | List all datasets |
| ``pixie dataset save <name> [--select MODE]`` | Save a span to a dataset |
| ``pixie dataset validate [path]`` | Validate dataset JSON files |
| ``pixie analyze <test_run_id>`` | Generate analysis and recommendations |

---

## Types

### `Evaluable`

```python
Evaluable(*, eval_input: JsonValue = None, eval_output: JsonValue = None, eval_metadata: dict[str, JsonValue] | None = None, expected_output: Union[JsonValue, pixie.storage.evaluable._Unset] = <_Unset.UNSET: 'UNSET'>, evaluators: list[str] | None = None, description: str | None = None, captured_output: dict[str, JsonValue] | None = None, captured_state: dict[str, JsonValue] | None = None) -> None
```

Uniform data carrier for evaluators.

All fields use Pydantic ``JsonValue`` to guarantee JSON
round-trip fidelity.  ``expected_output`` uses a union with the
``_Unset`` sentinel so callers can distinguish *"expected output
was not provided"* from *"expected output is explicitly None"*.

Attributes:
    eval_input: The primary input to the observed operation.
    eval_output: The primary output of the observed operation.
    eval_metadata: Supplementary metadata (``None`` when absent).
    expected_output: The expected/reference output for evaluation.
        Defaults to ``UNSET`` (not provided). May be explicitly
        set to ``None`` to indicate "there is no expected output".
    captured_output: Captured output data from ``wrap(purpose="output")``,
        keyed by wrap name.
    captured_state: Captured state data from ``wrap(purpose="state")``,
        keyed by wrap name.

### `Evaluation`

```python
Evaluation(score: 'float', reasoning: 'str', details: 'dict[str, Any]' = <factory>) -> None
```

The result of a single evaluator applied to a single test case.

Attributes:
    score: Evaluation score between 0.0 and 1.0.
    reasoning: Human-readable explanation (required).
    details: Arbitrary JSON-serializable metadata.

### `ScoreThreshold`

```python
ScoreThreshold(threshold: 'float' = 0.5, pct: 'float' = 1.0) -> None
```

Pass criteria: *pct* fraction of inputs must score >= *threshold* on all evaluators.

Attributes:
    threshold: Minimum score an individual evaluation must reach.
    pct: Fraction of test-case inputs (0.0–1.0) that must pass.

## Eval Functions

### `pixie.run_and_evaluate`

```python
pixie.run_and_evaluate(evaluator: 'Callable[..., Any]', runnable: 'Callable[..., Any]', eval_input: 'Any', *, expected_output: 'Any' = <object object at 0x7788c2ad5c80>, from_trace: 'Callable[[list[ObservationNode]], Evaluable] | None' = None) -> 'Evaluation'
```

Run *runnable(eval_input)* while capturing traces, then evaluate.

Convenience wrapper combining ``_run_and_capture`` and ``evaluate``.
The runnable is called exactly once.

Args:
    evaluator: An evaluator callable (sync or async).
    runnable: The application function to test.
    eval_input: The single input passed to *runnable*.
    expected_output: Optional expected value merged into the
        evaluable.
    from_trace: Optional callable to select a specific span from
        the trace tree for evaluation.

Returns:
    The ``Evaluation`` result.

Raises:
    ValueError: If no spans were captured during execution.

### `pixie.assert_pass`

```python
pixie.assert_pass(runnable: 'Callable[..., Any]', eval_inputs: 'list[Any]', evaluators: 'list[Callable[..., Any]]', *, evaluables: 'list[Evaluable] | None' = None, pass_criteria: 'Callable[[list[list[Evaluation]]], tuple[bool, str]] | None' = None, from_trace: 'Callable[[list[ObservationNode]], Evaluable] | None' = None) -> 'None'
```

Run evaluators against a runnable over multiple inputs.

For each input, runs the runnable once via ``_run_and_capture``,
then evaluates with every evaluator concurrently via
``asyncio.gather``.

The results matrix has shape ``[eval_inputs][evaluators]``.
If the pass criteria are not met, raises :class:`EvalAssertionError`
carrying the matrix.

When ``evaluables`` is provided, behaviour depends on whether each
item already has ``eval_output`` populated:

- **eval_output is None** — the ``runnable`` is called via
  ``run_and_evaluate`` to produce an output from traces, and
  ``expected_output`` from the evaluable is merged into the result.
- **eval_output is not None** — the evaluable is used directly
  (the runnable is not called for that item).

Args:
    runnable: The application function to test.
    eval_inputs: List of inputs, each passed to *runnable*.
    evaluators: List of evaluator callables.
    evaluables: Optional list of ``Evaluable`` items, one per input.
        When provided, their ``expected_output`` is forwarded to
        ``run_and_evaluate``.  Must have the same length as
        *eval_inputs*.
    pass_criteria: Receives the results matrix, returns
        ``(passed, message)``.  Defaults to ``ScoreThreshold()``.
    from_trace: Optional span selector forwarded to
        ``run_and_evaluate``.

Raises:
    EvalAssertionError: When pass criteria are not met.
    ValueError: When *evaluables* length does not match *eval_inputs*.

### `pixie.assert_dataset_pass`

```python
pixie.assert_dataset_pass(runnable: 'Callable[..., Any]', dataset_name: 'str', evaluators: 'list[Callable[..., Any]]', *, dataset_dir: 'str | None' = None, pass_criteria: 'Callable[[list[list[Evaluation]]], tuple[bool, str]] | None' = None, from_trace: 'Callable[[list[ObservationNode]], Evaluable] | None' = None) -> 'None'
```

Load a dataset by name, then run ``assert_pass`` with its items.

This is a convenience wrapper that:

1. Loads the dataset from the ``DatasetStore``.
2. Extracts ``eval_input`` from each item as the runnable inputs.
3. Uses the full ``Evaluable`` items (which carry ``expected_output``)
   as the evaluables.
4. Delegates to ``assert_pass``.

Args:
    runnable: The application function to test.
    dataset_name: Name of the dataset to load.
    evaluators: List of evaluator callables.
    dataset_dir: Override directory for the dataset store.
        When ``None``, reads from ``PixieConfig.dataset_dir``.
    pass_criteria: Receives the results matrix, returns
        ``(passed, message)``.
    from_trace: Optional span selector forwarded to
        ``assert_pass``.

Raises:
    FileNotFoundError: If no dataset with *dataset_name* exists.
    EvalAssertionError: When pass criteria are not met.

## Trace Helpers

### `pixie.last_llm_call`

```python
pixie.last_llm_call(trace: 'list[ObservationNode]') -> 'Evaluable'
```

Find the ``LLMSpan`` with the latest ``ended_at`` in the trace tree.

Args:
    trace: The trace tree (list of root ``ObservationNode`` instances).

Returns:
    An ``Evaluable`` wrapping the most recently ended ``LLMSpan``.

Raises:
    ValueError: If no ``LLMSpan`` exists in the trace.

### `pixie.root`

```python
pixie.root(trace: 'list[ObservationNode]') -> 'Evaluable'
```

Return the first root node's span as ``Evaluable``.

Args:
    trace: The trace tree (list of root ``ObservationNode`` instances).

Returns:
    An ``Evaluable`` wrapping the first root node's span.

Raises:
    ValueError: If the trace is empty.

### `pixie.capture_traces`

```python
pixie.capture_traces() -> 'Generator[MemoryTraceHandler, None, None]'
```

Context manager that installs a ``MemoryTraceHandler`` and yields it.

Calls ``init()`` (no-op if already initialised) then registers the
handler via ``add_handler()``.  On exit the handler is removed and
the delivery queue is flushed so that all spans are available on
``handler.spans``.
