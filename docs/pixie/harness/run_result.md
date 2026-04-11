Module pixie.harness.run_result
===============================
Test result models and persistence for ``pixie test``.

Provides:
- :class:`EvaluationResult` — result of one evaluator on one entry.
- :class:`EntryResult` — results for a single dataset entry.
- :class:`DatasetResult` — results for a single dataset.
- :class:`RunResult` — top-level result container.
- :func:`save_test_result` — write result JSON to disk.
- :func:`load_test_result` — read result JSON from disk.
- :func:`generate_test_id` — create a timestamped test run ID.

Functions
---------

`def generate_test_id() ‑> str`
:   Generate a timestamped test run ID.
    
    Returns:
        A string of the form ``YYYYMMDD-HHMMSS``.

`def load_test_result(test_id: str) ‑> pixie.harness.run_result.RunResult`
:   Load a test result from ``<pixie_root>/results/<test_id>/result.json``.
    
    Also reads any ``dataset-<index>.md`` analysis files and attaches
    their content to the corresponding :class:`DatasetResult`.
    
    Args:
        test_id: The test run identifier.
    
    Returns:
        The deserialized :class:`RunResult`.
    
    Raises:
        FileNotFoundError: If the result file does not exist.

`def save_test_result(result: RunResult) ‑> str`
:   Write test result JSON to ``<pixie_root>/results/<test_id>/result.json``.
    
    Also writes per-entry ``entry-{i}/entry.json`` files so that each
    entry's data (input, output, evaluations, trace path) is accessible
    individually — e.g. for agent-driven grading of pending evaluations.
    
    Args:
        result: The test run result to persist.
    
    Returns:
        The absolute path of the saved JSON file.

Classes
-------

`DatasetResult(dataset: str, entries: list[EntryResult], analysis: str | None = None)`
:   Results for a single dataset evaluation run.
    
    Attributes:
        dataset: Dataset name.
        entries: Per-entry results.
        analysis: Markdown analysis content (None until ``pixie analyze`` runs).

    ### Instance variables

    `analysis: str | None`
    :

    `dataset: str`
    :

    `entries: list[pixie.harness.run_result.EntryResult]`
    :

`EntryResult(input: JsonValue, output: JsonValue, expected_output: JsonValue | None, description: str | None, evaluations: list[EvaluationResult | PendingEvaluation], trace_file: str | None = None, analysis: str | None = None)`
:   Results for a single dataset entry.
    
    Attributes:
        input: The eval input value.
        output: The eval output value.
        expected_output: The expected output (None if not provided).
        description: One-sentence scenario description (None if not provided).
        evaluations: Completed and pending evaluator results for this entry.
        trace_file: Relative path to per-entry JSONL trace file (None if not captured).
        analysis: Per-entry analysis markdown (None until agent fills it in).

    ### Instance variables

    `analysis: str | None`
    :

    `description: str | None`
    :

    `evaluations: list[pixie.harness.run_result.EvaluationResult | pixie.harness.run_result.PendingEvaluation]`
    :

    `expected_output: JsonValue | None`
    :

    `input: JsonValue`
    :

    `output: JsonValue`
    :

    `trace_file: str | None`
    :

`EvaluationResult(evaluator: str, score: float, reasoning: str)`
:   Result of a single evaluator on a single entry.
    
    Attributes:
        evaluator: Display name of the evaluator.
        score: Score between 0.0 and 1.0.
        reasoning: Human-readable explanation.

    ### Instance variables

    `evaluator: str`
    :

    `reasoning: str`
    :

    `score: float`
    :

`PendingEvaluation(evaluator: str, criteria: str)`
:   An evaluation awaiting agent grading.
    
    Attributes:
        evaluator: Display name of the agent evaluator.
        criteria: Grading instructions for the agent.

    ### Instance variables

    `criteria: str`
    :

    `evaluator: str`
    :

`RunResult(test_id: str, command: str, started_at: str, ended_at: str, datasets: list[DatasetResult] = <factory>)`
:   Top-level test run result container.
    
    Attributes:
        test_id: Unique identifier for this test run.
        command: The command string that produced this result.
        started_at: ISO 8601 UTC timestamp when the test run started.
        ended_at: ISO 8601 UTC timestamp when the test run ended.
        datasets: Per-dataset results.

    ### Instance variables

    `command: str`
    :

    `datasets: list[pixie.harness.run_result.DatasetResult]`
    :

    `ended_at: str`
    :

    `started_at: str`
    :

    `test_id: str`
    :