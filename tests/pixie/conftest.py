"""Shared test helpers for pixie tests."""

from __future__ import annotations

from typing import Any

from pydantic import JsonValue

from pixie.eval.evaluable import NamedData
from pixie.harness.run_result import (
    DatasetResult,
    EntryResult,
    EvaluationResult,
    PendingEvaluation,
)


def make_entry(
    *,
    input: JsonValue = None,
    output: JsonValue = None,
    expected_output: JsonValue | None = None,
    description: str | None = None,
    evaluations: list[EvaluationResult | PendingEvaluation] | None = None,
    trace_file: str | None = None,
    analysis: str | None = None,
    evaluators: list[str] | None = None,
    eval_metadata: dict[str, Any] | None = None,
) -> EntryResult:
    """Build an EntryResult from collapsed input/output values.

    Wraps the values in single-item NamedData lists for the new model.
    """
    evals = evaluations or []
    eval_names = evaluators or [ev.evaluator for ev in evals]
    eval_input = (
        [NamedData(name="input_data", value=input)] if input is not None else []
    )
    eval_output = [NamedData(name="output", value=output)] if output is not None else []
    return EntryResult(
        eval_input=eval_input,
        eval_output=eval_output,
        evaluations=evals,
        expectation=expected_output,
        evaluators=eval_names,
        eval_metadata=eval_metadata,
        description=description,
        trace_file=trace_file,
        analysis=analysis,
    )


def make_dataset(
    dataset: str,
    entries: list[EntryResult],
    *,
    dataset_path: str = "",
    runnable: str = "",
    analysis: str | None = None,
) -> DatasetResult:
    """Build a DatasetResult with default path/runnable values."""
    return DatasetResult(
        dataset=dataset,
        dataset_path=dataset_path,
        runnable=runnable,
        entries=entries,
        analysis=analysis,
    )
