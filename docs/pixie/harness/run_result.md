Module pixie.harness.run_result
===============================
Test result models and persistence for ``pixie test``.

Provides:
- :class:`EvaluationResult` — result of one evaluator on one entry.
- :class:`EntryResult` — results for a single dataset entry.
- :class:`DatasetResult` — results for a single dataset.
- :class:`RunResult` — top-level result container.
- :func:`save_test_result` — write result artifacts to disk.
- :func:`load_test_result` — read result artifacts from disk.
- :func:`generate_test_id` — create a timestamped test run ID.

On-disk layout::

    results/{test_id}/
      meta.json
      dataset-{idx}/
        metadata.json
        entry-{idx}/
          config.json
          eval-input.jsonl
          eval-output.jsonl
          evaluations.jsonl
          trace.jsonl        (written by test_command)

Functions
---------

`def generate_test_id() ‑> str`
:   Generate a timestamped test run ID.
    
    Returns:
        A string of the form ``YYYYMMDD-HHMMSS``.

`def load_test_result(test_id: str) ‑> pixie.harness.run_result.RunResult`
:   Load a test result from the per-entry directory structure.
    
    Reads ``meta.json``, per-dataset ``metadata.json``, and per-entry
    ``config.json``/``eval-input.jsonl``/``eval-output.jsonl``/
    ``evaluations.jsonl`` files.  Also reads ``analysis.md`` files
    if present.
    
    Args:
        test_id: The test run identifier.
    
    Returns:
        The deserialized :class:`RunResult`.
    
    Raises:
        FileNotFoundError: If the result directory or meta.json does not exist.

`def save_test_result(result: RunResult) ‑> str`
:   Write test result artifacts to the per-entry directory structure.
    
    Layout::
    
        results/{test_id}/
          meta.json
          dataset-{idx}/
            metadata.json
            entry-{idx}/
              config.json
              eval-input.jsonl
              eval-output.jsonl
              evaluations.jsonl
    
    Args:
        result: The test run result to persist.
    
    Returns:
        The absolute path of the result directory.

Classes
-------

`DatasetResult(dataset: str, dataset_path: str, runnable: str, entries: list[EntryResult], analysis: str | None = None)`
:   Results for a single dataset evaluation run.
    
    Attributes:
        dataset: Dataset name.
        dataset_path: Original path of the dataset file.
        runnable: Configured runnable reference string.
        entries: Per-entry results.
        analysis: Markdown analysis content (None until agent fills it in).

    ### Instance variables

    `analysis: str | None`
    :

    `dataset: str`
    :

    `dataset_path: str`
    :

    `entries: list[pixie.harness.run_result.EntryResult]`
    :

    `runnable: str`
    :

`EntryResult(eval_input: list[NamedData], eval_output: list[NamedData], evaluations: list[EvaluationResult | PendingEvaluation], expectation: JsonValue | None, evaluators: list[str], eval_metadata: dict[str, JsonValue] | None, description: str | None, trace_file: str | None = None, analysis: str | None = None)`
:   Results for a single dataset entry.
    
    Canonical data is stored in ``eval_input`` and ``eval_output`` as
    :class:`NamedData` lists.  The collapsed ``input`` / ``output`` /
    ``expected_output`` properties exist for display compatibility.
    
    Attributes:
        eval_input: Named input data items fed to evaluators.
        eval_output: Named output data items produced by the app.
        evaluations: Completed and pending evaluator results for this entry.
        expectation: The expected output (None if not provided).
        evaluators: Fully-expanded evaluator name list.
        eval_metadata: Per-entry metadata dict (None if not provided).
        description: One-sentence scenario description (None if not provided).
        trace_file: Relative path to per-entry JSONL trace file (None if not captured).
        analysis: Per-entry analysis markdown (None until agent fills it in).

    ### Instance variables

    `analysis: str | None`
    :

    `description: str | None`
    :

    `eval_input: list[pixie.eval.evaluable.NamedData]`
    :

    `eval_metadata: dict[str, JsonValue] | None`
    :

    `eval_output: list[pixie.eval.evaluable.NamedData]`
    :

    `evaluations: list[pixie.harness.run_result.EvaluationResult | pixie.harness.run_result.PendingEvaluation]`
    :

    `evaluators: list[str]`
    :

    `expectation: JsonValue | None`
    :

    `expected_output: JsonValue | None`
    :   Alias for ``expectation`` for backward compatibility.

    `input: JsonValue`
    :   Collapsed eval_input for display.

    `output: JsonValue`
    :   Collapsed eval_output for display.

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