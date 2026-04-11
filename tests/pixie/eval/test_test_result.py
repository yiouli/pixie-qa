"""Tests for pixie.evals.test_result — result models and persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pixie.harness.run_result import (
    DatasetResult,
    EntryResult,
    EvaluationResult,
    PendingEvaluation,
    RunResult,
    generate_test_id,
    load_test_result,
    save_test_result,
)


class TestGenerateTestId:
    """Tests for generate_test_id()."""

    def test_format_is_timestamp(self) -> None:
        test_id = generate_test_id()
        # Should match YYYYMMDD-HHMMSS
        assert len(test_id) == 15
        assert test_id[8] == "-"

    def test_returns_string(self) -> None:
        assert isinstance(generate_test_id(), str)


class TestEvaluationResult:
    """Tests for EvaluationResult dataclass."""

    def test_frozen(self) -> None:
        ev = EvaluationResult(evaluator="Factuality", score=0.9, reasoning="Good")
        with pytest.raises(AttributeError):
            ev.score = 0.5  # type: ignore[misc]


class TestEntryResult:
    """Tests for EntryResult dataclass."""

    def test_frozen(self) -> None:
        entry = EntryResult(
            input="test",
            output="result",
            expected_output=None,
            description=None,
            evaluations=[],
        )
        with pytest.raises(AttributeError):
            entry.input = "changed"  # type: ignore[misc]


def _make_test_result() -> RunResult:
    """Create a sample RunResult for testing."""
    return RunResult(
        test_id="20260403-120000",
        command="pixie test tests/manual/datasets/sample-qa.json",
        started_at="2026-04-03T12:00:00Z",
        ended_at="2026-04-03T12:00:05Z",
        datasets=[
            DatasetResult(
                dataset="sample-qa",
                entries=[
                    EntryResult(
                        input={"question": "What is 2+2?"},
                        output="4",
                        expected_output="4",
                        description="Basic arithmetic check",
                        evaluations=[
                            EvaluationResult(
                                evaluator="Factuality",
                                score=1.0,
                                reasoning="Correct",
                            ),
                            EvaluationResult(
                                evaluator="ExactMatch",
                                score=1.0,
                                reasoning="Exact match",
                            ),
                        ],
                    ),
                    EntryResult(
                        input={"question": "Capital of France?"},
                        output="London",
                        expected_output="Paris",
                        description="Geography knowledge",
                        evaluations=[
                            EvaluationResult(
                                evaluator="Factuality",
                                score=0.2,
                                reasoning="Incorrect",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


class TestSaveAndLoadTestResult:
    """Tests for save_test_result and load_test_result round-trip."""

    def test_round_trip(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        result = _make_test_result()

        filepath = save_test_result(result)

        assert filepath.endswith("result.json")
        assert "results/20260403-120000" in filepath

        # Verify JSON structure
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        assert data["meta"]["testId"] == "20260403-120000"
        assert len(data["datasets"]) == 1
        assert data["datasets"][0]["dataset"] == "sample-qa"
        assert len(data["datasets"][0]["entries"]) == 2
        assert (
            data["datasets"][0]["entries"][0]["description"] == "Basic arithmetic check"
        )
        assert data["datasets"][0]["entries"][0]["expectedOutput"] == "4"

    def test_load_round_trip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        original = _make_test_result()
        save_test_result(original)

        loaded = load_test_result("20260403-120000")

        assert loaded.test_id == original.test_id
        assert loaded.command == original.command
        assert len(loaded.datasets) == 1
        ds = loaded.datasets[0]
        assert ds.dataset == "sample-qa"
        assert len(ds.entries) == 2
        assert ds.entries[0].description == "Basic arithmetic check"
        assert ds.entries[0].evaluations[0].evaluator == "Factuality"
        ev0 = ds.entries[0].evaluations[0]
        assert isinstance(ev0, EvaluationResult)
        assert ev0.score == 1.0
        ev1 = ds.entries[1].evaluations[0]
        assert isinstance(ev1, EvaluationResult)
        assert ev1.score == 0.2

    def test_load_with_analysis(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        result = _make_test_result()
        save_test_result(result)

        # Write analysis markdown
        analysis_path = tmp_path / "results" / "20260403-120000" / "dataset-0.md"
        analysis_path.write_text("## Analysis\nAll good.", encoding="utf-8")

        loaded = load_test_result("20260403-120000")
        assert loaded.datasets[0].analysis == "## Analysis\nAll good."

    def test_load_missing_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        with pytest.raises(FileNotFoundError):
            load_test_result("nonexistent")


class TestPendingEvaluation:
    """Tests for PendingEvaluation dataclass."""

    def test_frozen(self) -> None:
        ev = PendingEvaluation(evaluator="ResponseQuality", criteria="Be helpful")
        with pytest.raises(AttributeError):
            ev.evaluator = "changed"  # type: ignore[misc]

    def test_fields(self) -> None:
        ev = PendingEvaluation(evaluator="ResponseQuality", criteria="Be helpful")
        assert ev.evaluator == "ResponseQuality"
        assert ev.criteria == "Be helpful"


class TestPendingEvaluationRoundTrip:
    """Tests for PendingEvaluation serialization and deserialization."""

    def _make_result_with_pending(self) -> RunResult:
        return RunResult(
            test_id="20260403-130000",
            command="pixie test tests/manual/datasets/sample-qa.json",
            started_at="2026-04-03T13:00:00Z",
            ended_at="2026-04-03T13:00:05Z",
            datasets=[
                DatasetResult(
                    dataset="sample-qa",
                    entries=[
                        EntryResult(
                            input={"question": "What is 2+2?"},
                            output="4",
                            expected_output="4",
                            description="Mixed evaluations",
                            evaluations=[
                                EvaluationResult(
                                    evaluator="ExactMatch",
                                    score=1.0,
                                    reasoning="Exact match",
                                ),
                                PendingEvaluation(
                                    evaluator="ResponseQuality",
                                    criteria="Rate the response quality.",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )

    def test_save_pending_has_status_field(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        result = self._make_result_with_pending()
        filepath = save_test_result(result)

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        evals = data["datasets"][0]["entries"][0]["evaluations"]
        assert len(evals) == 2
        assert evals[0]["evaluator"] == "ExactMatch"
        assert evals[0].get("status") is None
        assert evals[1]["evaluator"] == "ResponseQuality"
        assert evals[1]["status"] == "pending"
        assert evals[1]["criteria"] == "Rate the response quality."

    def test_load_round_trip_preserves_pending(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        result = self._make_result_with_pending()
        save_test_result(result)

        loaded = load_test_result("20260403-130000")
        entry = loaded.datasets[0].entries[0]
        assert len(entry.evaluations) == 2

        ev0 = entry.evaluations[0]
        assert isinstance(ev0, EvaluationResult)
        assert ev0.evaluator == "ExactMatch"
        assert ev0.score == 1.0

        ev1 = entry.evaluations[1]
        assert isinstance(ev1, PendingEvaluation)
        assert ev1.evaluator == "ResponseQuality"
        assert ev1.criteria == "Rate the response quality."

    def test_optional_fields_omitted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        result = RunResult(
            test_id="20260403-120001",
            command="pixie test foo.json",
            started_at="2026-04-03T12:00:00Z",
            ended_at="2026-04-03T12:00:01Z",
            datasets=[
                DatasetResult(
                    dataset="no-desc",
                    entries=[
                        EntryResult(
                            input="hi",
                            output="hello",
                            expected_output=None,
                            description=None,
                            evaluations=[],
                        ),
                    ],
                ),
            ],
        )
        filepath = save_test_result(result)

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        entry = data["datasets"][0]["entries"][0]
        assert "expectedOutput" not in entry
        assert "description" not in entry


class TestPerEntryFiles:
    """Tests for per-entry JSON files written by save_test_result."""

    def test_per_entry_json_files_created(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        result = _make_test_result()
        save_test_result(result)

        result_dir = tmp_path / "results" / "20260403-120000"
        entry_0 = result_dir / "entry-0" / "entry.json"
        entry_1 = result_dir / "entry-1" / "entry.json"
        assert entry_0.is_file()
        assert entry_1.is_file()

    def test_per_entry_json_content(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        result = _make_test_result()
        save_test_result(result)

        result_dir = tmp_path / "results" / "20260403-120000"
        with open(result_dir / "entry-0" / "entry.json", encoding="utf-8") as f:
            data = json.load(f)

        assert data["input"] == {"question": "What is 2+2?"}
        assert data["output"] == "4"
        assert data["expectedOutput"] == "4"
        assert data["description"] == "Basic arithmetic check"
        assert data["dataset"] == "sample-qa"
        assert data["entryIndex"] == 0
        assert len(data["evaluations"]) == 2

    def test_per_entry_json_with_pending(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        result = RunResult(
            test_id="20260403-140000",
            command="pixie test foo.json",
            started_at="2026-04-03T14:00:00Z",
            ended_at="2026-04-03T14:00:05Z",
            datasets=[
                DatasetResult(
                    dataset="mixed",
                    entries=[
                        EntryResult(
                            input="q",
                            output="a",
                            expected_output=None,
                            description="Mixed entry",
                            evaluations=[
                                EvaluationResult(
                                    evaluator="ExactMatch",
                                    score=1.0,
                                    reasoning="OK",
                                ),
                                PendingEvaluation(
                                    evaluator="Quality",
                                    criteria="Is it good?",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        save_test_result(result)

        result_dir = tmp_path / "results" / "20260403-140000"
        with open(result_dir / "entry-0" / "entry.json", encoding="utf-8") as f:
            data = json.load(f)

        assert len(data["evaluations"]) == 2
        assert data["evaluations"][0]["evaluator"] == "ExactMatch"
        assert data["evaluations"][0]["score"] == 1.0
        assert data["evaluations"][1]["evaluator"] == "Quality"
        assert data["evaluations"][1]["status"] == "pending"
        assert data["evaluations"][1]["criteria"] == "Is it good?"
