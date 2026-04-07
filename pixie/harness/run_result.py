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
class EntryResult:
    """Results for a single dataset entry.

    Attributes:
        input: The eval input value.
        output: The eval output value.
        expected_output: The expected output (None if not provided).
        description: One-sentence scenario description (None if not provided).
        evaluations: List of evaluator results for this entry.
    """

    input: JsonValue
    output: JsonValue
    expected_output: JsonValue | None
    description: str | None
    evaluations: list[EvaluationResult]


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


def _result_to_dict(result: RunResult) -> list[dict[str, Any]]:
    """Serialize a :class:`RunResult` to the spec JSON shape.

    The top-level is an array of dataset objects, matching the spec:
    ``[{"dataset": ..., "entries": [...]}]``
    """
    datasets: list[dict[str, Any]] = []
    for ds in result.datasets:
        entry_dicts: list[dict[str, Any]] = []
        for entry in ds.entries:
            eval_dicts = [
                {
                    "evaluator": ev.evaluator,
                    "score": ev.score,
                    "reasoning": ev.reasoning,
                }
                for ev in entry.evaluations
            ]
            entry_dict: dict[str, Any] = {
                "input": entry.input,
                "output": entry.output,
                "evaluations": eval_dicts,
            }
            if entry.expected_output is not None:
                entry_dict["expectedOutput"] = entry.expected_output
            if entry.description is not None:
                entry_dict["description"] = entry.description
            entry_dicts.append(entry_dict)
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
            evaluations = [
                EvaluationResult(
                    evaluator=ev["evaluator"],
                    score=ev["score"],
                    reasoning=ev["reasoning"],
                )
                for ev in entry_data["evaluations"]
            ]
            entries.append(
                EntryResult(
                    input=entry_data["input"],
                    output=entry_data["output"],
                    expected_output=entry_data.get("expectedOutput"),
                    description=entry_data.get("description"),
                    evaluations=evaluations,
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
