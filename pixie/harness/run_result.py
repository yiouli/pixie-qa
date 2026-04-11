"""Test result models and persistence for ``pixie test``.

Provides:
- :class:`EvaluationResult` — result of one evaluator on one entry.
- :class:`EntryResult` — results for a single dataset entry.
- :class:`DatasetResult` — results for a single dataset.
- :class:`RunResult` — top-level result container.
- :func:`save_test_result` — write result JSON to disk.
- :func:`load_test_result` — read result JSON from disk.
- :func:`generate_test_id` — create a timestamped test run ID.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pydantic import JsonValue


def generate_test_id() -> str:
    """Generate a timestamped test run ID.

    Returns:
        A string of the form ``YYYYMMDD-HHMMSS``.
    """
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


@dataclass(frozen=True)
class EvaluationResult:
    """Result of a single evaluator on a single entry.

    Attributes:
        evaluator: Display name of the evaluator.
        score: Score between 0.0 and 1.0.
        reasoning: Human-readable explanation.
    """

    evaluator: str
    score: float
    reasoning: str


@dataclass(frozen=True)
class PendingEvaluation:
    """An evaluation awaiting agent grading.

    Attributes:
        evaluator: Display name of the agent evaluator.
        criteria: Grading instructions for the agent.
    """

    evaluator: str
    criteria: str


@dataclass(frozen=True)
class EntryResult:
    """Results for a single dataset entry.

    Attributes:
        input: The eval input value.
        output: The eval output value.
        expected_output: The expected output (None if not provided).
        description: One-sentence scenario description (None if not provided).
        evaluations: Completed and pending evaluator results for this entry.
        trace_file: Relative path to per-entry JSONL trace file (None if not captured).
        analysis: Per-entry analysis markdown (None until agent fills it in).
    """

    input: JsonValue
    output: JsonValue
    expected_output: JsonValue | None
    description: str | None
    evaluations: list[EvaluationResult | PendingEvaluation]
    trace_file: str | None = None
    analysis: str | None = None


@dataclass
class DatasetResult:
    """Results for a single dataset evaluation run.

    Attributes:
        dataset: Dataset name.
        entries: Per-entry results.
        analysis: Markdown analysis content (None until ``pixie analyze`` runs).
    """

    dataset: str
    entries: list[EntryResult]
    analysis: str | None = None


@dataclass
class RunResult:
    """Top-level test run result container.

    Attributes:
        test_id: Unique identifier for this test run.
        command: The command string that produced this result.
        started_at: ISO 8601 UTC timestamp when the test run started.
        ended_at: ISO 8601 UTC timestamp when the test run ended.
        datasets: Per-dataset results.
    """

    test_id: str
    command: str
    started_at: str
    ended_at: str
    datasets: list[DatasetResult] = field(default_factory=list)


def _entry_to_dict(entry: EntryResult) -> dict[str, Any]:
    """Serialize a single :class:`EntryResult` to a JSON-ready dict."""
    eval_dicts: list[dict[str, Any]] = []
    for ev in entry.evaluations:
        if isinstance(ev, PendingEvaluation):
            eval_dicts.append(
                {
                    "evaluator": ev.evaluator,
                    "status": "pending",
                    "criteria": ev.criteria,
                }
            )
        else:
            eval_dicts.append(
                {
                    "evaluator": ev.evaluator,
                    "score": ev.score,
                    "reasoning": ev.reasoning,
                }
            )
    entry_dict: dict[str, Any] = {
        "input": entry.input,
        "output": entry.output,
        "evaluations": eval_dicts,
    }
    if entry.expected_output is not None:
        entry_dict["expectedOutput"] = entry.expected_output
    if entry.description is not None:
        entry_dict["description"] = entry.description
    if entry.trace_file is not None:
        entry_dict["traceFile"] = entry.trace_file
    if entry.analysis is not None:
        entry_dict["analysis"] = entry.analysis
    return entry_dict


def _result_to_dict(result: RunResult) -> list[dict[str, Any]]:
    """Serialize a :class:`RunResult` to the spec JSON shape.

    The top-level is an array of dataset objects, matching the spec:
    ``[{"dataset": ..., "entries": [...]}]``
    """
    datasets: list[dict[str, Any]] = []
    for ds in result.datasets:
        entry_dicts: list[dict[str, Any]] = []
        for entry in ds.entries:
            entry_dicts.append(_entry_to_dict(entry))
        ds_dict: dict[str, Any] = {
            "dataset": ds.dataset,
            "entries": entry_dicts,
        }
        datasets.append(ds_dict)
    return datasets


def _metadata_to_dict(result: RunResult) -> dict[str, Any]:
    """Serialize the test run metadata (stored alongside the data array)."""
    return {
        "testId": result.test_id,
        "command": result.command,
        "startedAt": result.started_at,
        "endedAt": result.ended_at,
    }


def save_test_result(result: RunResult) -> str:
    """Write test result JSON to ``<pixie_root>/results/<test_id>/result.json``.

    Also writes per-entry ``entry-{i}/entry.json`` files so that each
    entry's data (input, output, evaluations, trace path) is accessible
    individually — e.g. for agent-driven grading of pending evaluations.

    Args:
        result: The test run result to persist.

    Returns:
        The absolute path of the saved JSON file.
    """
    from pixie.config import get_config

    config = get_config()
    result_dir = os.path.join(config.root, "results", result.test_id)
    os.makedirs(result_dir, exist_ok=True)

    filepath = os.path.join(result_dir, "result.json")
    payload = {
        "meta": _metadata_to_dict(result),
        "datasets": _result_to_dict(result),
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    # Write per-entry JSON files for agent-driven entry-by-entry processing.
    entry_index = 0
    for ds in result.datasets:
        for entry in ds.entries:
            entry_dir = os.path.join(result_dir, f"entry-{entry_index}")
            os.makedirs(entry_dir, exist_ok=True)
            entry_path = os.path.join(entry_dir, "entry.json")
            entry_payload = _entry_to_dict(entry)
            entry_payload["dataset"] = ds.dataset
            entry_payload["entryIndex"] = entry_index
            with open(entry_path, "w", encoding="utf-8") as ef:
                json.dump(entry_payload, ef, indent=2, ensure_ascii=False)
            entry_index += 1

    return os.path.abspath(filepath)


def load_test_result(test_id: str) -> RunResult:
    """Load a test result from ``<pixie_root>/results/<test_id>/result.json``.

    Also reads any ``dataset-<index>.md`` analysis files and attaches
    their content to the corresponding :class:`DatasetResult`.

    Args:
        test_id: The test run identifier.

    Returns:
        The deserialized :class:`RunResult`.

    Raises:
        FileNotFoundError: If the result file does not exist.
    """
    from pixie.config import get_config

    config = get_config()
    result_dir = os.path.join(config.root, "results", test_id)
    filepath = os.path.join(result_dir, "result.json")

    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    meta = data["meta"]
    datasets: list[DatasetResult] = []
    for i, ds_data in enumerate(data["datasets"]):
        entries: list[EntryResult] = []
        for entry_data in ds_data["entries"]:
            evaluations: list[EvaluationResult | PendingEvaluation] = []
            for ev in entry_data["evaluations"]:
                if ev.get("status") == "pending":
                    evaluations.append(
                        PendingEvaluation(
                            evaluator=ev["evaluator"],
                            criteria=ev.get("criteria", ""),
                        )
                    )
                else:
                    evaluations.append(
                        EvaluationResult(
                            evaluator=ev["evaluator"],
                            score=ev["score"],
                            reasoning=ev["reasoning"],
                        )
                    )
            entries.append(
                EntryResult(
                    input=entry_data["input"],
                    output=entry_data["output"],
                    expected_output=entry_data.get("expectedOutput"),
                    description=entry_data.get("description"),
                    evaluations=evaluations,
                    trace_file=entry_data.get("traceFile"),
                    analysis=entry_data.get("analysis"),
                )
            )

        # Load analysis markdown if it exists
        analysis_path = os.path.join(result_dir, f"dataset-{i}.md")
        analysis: str | None = None
        if os.path.isfile(analysis_path):
            with open(analysis_path, encoding="utf-8") as af:
                analysis = af.read()

        datasets.append(
            DatasetResult(
                dataset=ds_data["dataset"], entries=entries, analysis=analysis
            )
        )

    return RunResult(
        test_id=meta["testId"],
        command=meta["command"],
        started_at=meta["startedAt"],
        ended_at=meta["endedAt"],
        datasets=datasets,
    )
