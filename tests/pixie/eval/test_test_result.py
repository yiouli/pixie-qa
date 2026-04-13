"""Tests for pixie.harness.run_result — result models and persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pixie.harness.run_result import (
    EvaluationResult,
    PendingEvaluation,
    RunResult,
    generate_test_id,
    load_test_result,
    save_test_result,
)
from tests.pixie.conftest import make_dataset, make_entry


class TestGenerateTestId:
    """Tests for generate_test_id()."""

    def test_format_is_timestamp(self) -> None:
        test_id = generate_test_id()
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
        entry = make_entry(input="test", output="result")
        with pytest.raises(AttributeError):
            entry.eval_input = []  # type: ignore[misc]

    def test_collapsed_properties(self) -> None:
        entry = make_entry(
            input={"question": "hi"},
            output="hello",
            expected_output="hello",
        )
        assert entry.input == {"question": "hi"}
        assert entry.output == "hello"
        assert entry.expected_output == "hello"


def _make_test_result() -> RunResult:
    """Create a sample RunResult for testing."""
    return RunResult(
        test_id="20260403-120000",
        command="pixie test tests/manual/datasets/sample-qa.json",
        started_at="2026-04-03T12:00:00Z",
        ended_at="2026-04-03T12:00:05Z",
        datasets=[
            make_dataset(
                "sample-qa",
                dataset_path="tests/manual/datasets/sample-qa.json",
                runnable="pixie_qa/run_app.py:AppRunnable",
                entries=[
                    make_entry(
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
                    make_entry(
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

    def test_save_creates_directory_structure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        result = _make_test_result()
        result_dir = save_test_result(result)

        assert result_dir.endswith("20260403-120000")
        rdir = Path(result_dir)

        # meta.json
        meta = json.loads((rdir / "meta.json").read_text())
        assert meta["testId"] == "20260403-120000"

        # dataset-0/metadata.json
        ds_meta = json.loads((rdir / "dataset-0" / "metadata.json").read_text())
        assert ds_meta["dataset"] == "sample-qa"
        assert ds_meta["runnable"] == "pixie_qa/run_app.py:AppRunnable"

        # dataset-0/entry-0/config.json
        config = json.loads(
            (rdir / "dataset-0" / "entry-0" / "config.json").read_text()
        )
        assert config["description"] == "Basic arithmetic check"
        assert config["expectation"] == "4"

        # dataset-0/entry-0/eval-input.jsonl
        input_lines = (
            (rdir / "dataset-0" / "entry-0" / "eval-input.jsonl")
            .read_text()
            .strip()
            .split("\n")
        )
        assert len(input_lines) >= 1
        assert json.loads(input_lines[0])["name"] == "input_data"

        # dataset-0/entry-0/evaluations.jsonl
        eval_lines = (
            (rdir / "dataset-0" / "entry-0" / "evaluations.jsonl")
            .read_text()
            .strip()
            .split("\n")
        )
        assert len(eval_lines) == 2
        assert json.loads(eval_lines[0])["evaluator"] == "Factuality"

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
        assert ds.dataset_path == "tests/manual/datasets/sample-qa.json"
        assert len(ds.entries) == 2
        assert ds.entries[0].description == "Basic arithmetic check"
        ev0 = ds.entries[0].evaluations[0]
        assert isinstance(ev0, EvaluationResult)
        assert ev0.score == 1.0
        ev1 = ds.entries[1].evaluations[0]
        assert isinstance(ev1, EvaluationResult)
        assert ev1.score == 0.2

    def test_load_with_dataset_analysis(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        result = _make_test_result()
        save_test_result(result)

        analysis_path = (
            tmp_path / "results" / "20260403-120000" / "dataset-0" / "analysis.md"
        )
        analysis_path.write_text("## Analysis\nAll good.", encoding="utf-8")

        loaded = load_test_result("20260403-120000")
        assert loaded.datasets[0].analysis == "## Analysis\nAll good."

    def test_load_with_entry_analysis(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        result = _make_test_result()
        save_test_result(result)

        entry_analysis = (
            tmp_path
            / "results"
            / "20260403-120000"
            / "dataset-0"
            / "entry-0"
            / "analysis.md"
        )
        entry_analysis.write_text("Entry analysis here.", encoding="utf-8")

        loaded = load_test_result("20260403-120000")
        assert loaded.datasets[0].entries[0].analysis == "Entry analysis here."
        assert loaded.datasets[0].entries[1].analysis is None

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
    """Tests for PendingEvaluation persistence."""

    def _make_result_with_pending(self) -> RunResult:
        return RunResult(
            test_id="20260403-130000",
            command="pixie test tests/manual/datasets/sample-qa.json",
            started_at="2026-04-03T13:00:00Z",
            ended_at="2026-04-03T13:00:05Z",
            datasets=[
                make_dataset(
                    "sample-qa",
                    entries=[
                        make_entry(
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

    def test_save_pending_in_evaluations_jsonl(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        result = self._make_result_with_pending()
        result_dir = save_test_result(result)

        evals_path = (
            Path(result_dir) / "dataset-0" / "entry-0" / "evaluations.jsonl"
        )
        lines = evals_path.read_text().strip().split("\n")
        evals = [json.loads(line) for line in lines]

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

    def test_optional_config_fields(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        result = RunResult(
            test_id="20260403-120001",
            command="pixie test foo.json",
            started_at="2026-04-03T12:00:00Z",
            ended_at="2026-04-03T12:00:01Z",
            datasets=[
                make_dataset(
                    "no-desc",
                    entries=[make_entry(input="hi", output="hello")],
                ),
            ],
        )
        result_dir = save_test_result(result)

        config = json.loads(
            (Path(result_dir) / "dataset-0" / "entry-0" / "config.json").read_text()
        )
        assert "expectation" not in config
        assert "description" not in config


class TestPerEntryFiles:
    """Tests for per-entry file structure."""

    def test_all_entry_files_created(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        result = _make_test_result()
        result_dir = Path(save_test_result(result))

        for entry_idx in range(2):
            entry_dir = result_dir / "dataset-0" / f"entry-{entry_idx}"
            assert (entry_dir / "config.json").is_file()
            assert (entry_dir / "eval-input.jsonl").is_file()
            assert (entry_dir / "eval-output.jsonl").is_file()
            assert (entry_dir / "evaluations.jsonl").is_file()

    def test_evaluations_jsonl_with_pending(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        result = RunResult(
            test_id="20260403-140000",
            command="pixie test foo.json",
            started_at="2026-04-03T14:00:00Z",
            ended_at="2026-04-03T14:00:05Z",
            datasets=[
                make_dataset(
                    "mixed",
                    entries=[
                        make_entry(
                            input="q",
                            output="a",
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
        result_dir = Path(save_test_result(result))

        evals_path = result_dir / "dataset-0" / "entry-0" / "evaluations.jsonl"
        lines = evals_path.read_text().strip().split("\n")
        evals = [json.loads(line) for line in lines]

        assert len(evals) == 2
        assert evals[0]["evaluator"] == "ExactMatch"
        assert evals[0]["score"] == 1.0
        assert evals[1]["evaluator"] == "Quality"
        assert evals[1]["status"] == "pending"
        assert evals[1]["criteria"] == "Is it good?"
