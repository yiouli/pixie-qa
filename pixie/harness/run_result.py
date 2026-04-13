"""Test result models and persistence for ``pixie test``.

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
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pydantic import JsonValue

from pixie.eval.evaluable import NamedData, collapse_named_data


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
    """

    eval_input: list[NamedData]
    eval_output: list[NamedData]
    evaluations: list[EvaluationResult | PendingEvaluation]
    expectation: JsonValue | None
    evaluators: list[str]
    eval_metadata: dict[str, JsonValue] | None
    description: str | None
    trace_file: str | None = None
    analysis: str | None = None

    # -- backward-compat display properties ----------------------------------

    @property
    def input(self) -> JsonValue:
        """Collapsed eval_input for display."""
        return collapse_named_data(self.eval_input)

    @property
    def output(self) -> JsonValue:
        """Collapsed eval_output for display."""
        return collapse_named_data(self.eval_output)

    @property
    def expected_output(self) -> JsonValue | None:
        """Alias for ``expectation`` for backward compatibility."""
        return self.expectation


@dataclass
class DatasetResult:
    """Results for a single dataset evaluation run.

    Attributes:
        dataset: Dataset name.
        dataset_path: Original path of the dataset file.
        runnable: Configured runnable reference string.
        entries: Per-entry results.
        analysis: Markdown analysis content (None until agent fills it in).
    """

    dataset: str
    dataset_path: str
    runnable: str
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


def _eval_to_dict(ev: EvaluationResult | PendingEvaluation) -> dict[str, Any]:
    """Serialize a single evaluation to a JSON-ready dict."""
    if isinstance(ev, PendingEvaluation):
        return {
            "evaluator": ev.evaluator,
            "status": "pending",
            "criteria": ev.criteria,
        }
    return {
        "evaluator": ev.evaluator,
        "score": ev.score,
        "reasoning": ev.reasoning,
    }


def _entry_to_dict(entry: EntryResult) -> dict[str, Any]:
    """Serialize a single :class:`EntryResult` to a frontend-compatible dict.

    Uses the collapsed ``input``/``output`` properties for display.
    """
    eval_dicts = [_eval_to_dict(ev) for ev in entry.evaluations]
    entry_dict: dict[str, Any] = {
        "input": entry.input,
        "output": entry.output,
        "evaluations": eval_dicts,
    }
    if entry.expectation is not None:
        entry_dict["expectedOutput"] = entry.expectation
    if entry.description is not None:
        entry_dict["description"] = entry.description
    if entry.trace_file is not None:
        entry_dict["traceFile"] = entry.trace_file
    if entry.analysis is not None:
        entry_dict["analysis"] = entry.analysis
    return entry_dict


def _result_to_dict(result: RunResult) -> list[dict[str, Any]]:
    """Serialize a :class:`RunResult` to the frontend JSON shape.

    ``[{"dataset": ..., "entries": [...]}]``
    """
    datasets: list[dict[str, Any]] = []
    for ds in result.datasets:
        entry_dicts = [_entry_to_dict(e) for e in ds.entries]
        ds_dict: dict[str, Any] = {
            "dataset": ds.dataset,
            "entries": entry_dicts,
        }
        if ds.analysis is not None:
            ds_dict["analysis"] = ds.analysis
        datasets.append(ds_dict)
    return datasets


def _metadata_to_dict(result: RunResult) -> dict[str, Any]:
    """Serialize the test run metadata."""
    return {
        "testId": result.test_id,
        "command": result.command,
        "startedAt": result.started_at,
        "endedAt": result.ended_at,
    }


# ---------------------------------------------------------------------------
# JSONL helpers
# ---------------------------------------------------------------------------


def _write_jsonl(path: str, items: list[dict[str, Any]]) -> None:
    """Write a list of dicts as JSONL (one JSON object per line)."""
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def _read_jsonl(path: str) -> list[dict[str, Any]]:
    """Read a JSONL file and return a list of dicts."""
    items: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


# ---------------------------------------------------------------------------
# Save / Load
# ---------------------------------------------------------------------------


def save_test_result(result: RunResult) -> str:
    """Write test result artifacts to the per-entry directory structure.

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
    """
    from pixie.config import get_config

    config = get_config()
    result_dir = os.path.join(config.root, "results", result.test_id)
    os.makedirs(result_dir, exist_ok=True)

    # Write meta.json
    meta_path = os.path.join(result_dir, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(_metadata_to_dict(result), f, indent=2, ensure_ascii=False)

    # Write per-dataset and per-entry files
    for ds_idx, ds in enumerate(result.datasets):
        ds_dir = os.path.join(result_dir, f"dataset-{ds_idx}")
        os.makedirs(ds_dir, exist_ok=True)

        # Dataset metadata
        ds_meta: dict[str, Any] = {
            "dataset": ds.dataset,
            "datasetPath": ds.dataset_path,
            "runnable": ds.runnable,
        }
        with open(os.path.join(ds_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(ds_meta, f, indent=2, ensure_ascii=False)

        for entry_idx, entry in enumerate(ds.entries):
            entry_dir = os.path.join(ds_dir, f"entry-{entry_idx}")
            os.makedirs(entry_dir, exist_ok=True)

            # config.json
            config_data: dict[str, Any] = {
                "evaluators": entry.evaluators,
            }
            if entry.description is not None:
                config_data["description"] = entry.description
            if entry.expectation is not None:
                config_data["expectation"] = entry.expectation
            if entry.eval_metadata is not None:
                config_data["evalMetadata"] = entry.eval_metadata
            with open(
                os.path.join(entry_dir, "config.json"), "w", encoding="utf-8"
            ) as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            # eval-input.jsonl
            _write_jsonl(
                os.path.join(entry_dir, "eval-input.jsonl"),
                [nd.model_dump() for nd in entry.eval_input],
            )

            # eval-output.jsonl
            _write_jsonl(
                os.path.join(entry_dir, "eval-output.jsonl"),
                [nd.model_dump() for nd in entry.eval_output],
            )

            # evaluations.jsonl
            _write_jsonl(
                os.path.join(entry_dir, "evaluations.jsonl"),
                [_eval_to_dict(ev) for ev in entry.evaluations],
            )

    return os.path.abspath(result_dir)


def load_test_result(test_id: str) -> RunResult:
    """Load a test result from the per-entry directory structure.

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
    """
    from pixie.config import get_config

    config = get_config()
    result_dir = os.path.join(config.root, "results", test_id)
    meta_path = os.path.join(result_dir, "meta.json")

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    datasets: list[DatasetResult] = []
    ds_idx = 0
    while True:
        ds_dir = os.path.join(result_dir, f"dataset-{ds_idx}")
        if not os.path.isdir(ds_dir):
            break

        # Read dataset metadata
        ds_meta_path = os.path.join(ds_dir, "metadata.json")
        with open(ds_meta_path, encoding="utf-8") as f:
            ds_meta = json.load(f)

        entries: list[EntryResult] = []
        entry_idx = 0
        while True:
            entry_dir = os.path.join(ds_dir, f"entry-{entry_idx}")
            if not os.path.isdir(entry_dir):
                break

            # config.json
            with open(
                os.path.join(entry_dir, "config.json"), encoding="utf-8"
            ) as f:
                entry_config = json.load(f)

            # eval-input.jsonl
            input_path = os.path.join(entry_dir, "eval-input.jsonl")
            raw_input = _read_jsonl(input_path) if os.path.isfile(input_path) else []
            eval_input = [NamedData(**item) for item in raw_input]

            # eval-output.jsonl
            output_path = os.path.join(entry_dir, "eval-output.jsonl")
            raw_output = _read_jsonl(output_path) if os.path.isfile(output_path) else []
            eval_output = [NamedData(**item) for item in raw_output]

            # evaluations.jsonl
            evals_path = os.path.join(entry_dir, "evaluations.jsonl")
            raw_evals = _read_jsonl(evals_path) if os.path.isfile(evals_path) else []
            evaluations: list[EvaluationResult | PendingEvaluation] = []
            for ev in raw_evals:
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

            # trace file
            trace_rel: str | None = None
            trace_path = os.path.join(entry_dir, "trace.jsonl")
            if os.path.isfile(trace_path):
                trace_rel = os.path.relpath(trace_path, result_dir)

            # entry analysis
            entry_analysis: str | None = None
            entry_analysis_path = os.path.join(entry_dir, "analysis.md")
            if os.path.isfile(entry_analysis_path):
                with open(entry_analysis_path, encoding="utf-8") as af:
                    entry_analysis = af.read()

            entries.append(
                EntryResult(
                    eval_input=eval_input,
                    eval_output=eval_output,
                    evaluations=evaluations,
                    expectation=entry_config.get("expectation"),
                    evaluators=entry_config.get("evaluators", []),
                    eval_metadata=entry_config.get("evalMetadata"),
                    description=entry_config.get("description"),
                    trace_file=trace_rel,
                    analysis=entry_analysis,
                )
            )
            entry_idx += 1

        # Dataset analysis
        ds_analysis: str | None = None
        ds_analysis_path = os.path.join(ds_dir, "analysis.md")
        if os.path.isfile(ds_analysis_path):
            with open(ds_analysis_path, encoding="utf-8") as af:
                ds_analysis = af.read()

        datasets.append(
            DatasetResult(
                dataset=ds_meta.get("dataset", f"dataset-{ds_idx}"),
                dataset_path=ds_meta.get("datasetPath", ""),
                runnable=ds_meta.get("runnable", ""),
                entries=entries,
                analysis=ds_analysis,
            )
        )
        ds_idx += 1

    return RunResult(
        test_id=meta["testId"],
        command=meta["command"],
        started_at=meta["startedAt"],
        ended_at=meta["endedAt"],
        datasets=datasets,
    )
