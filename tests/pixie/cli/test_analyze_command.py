"""Tests for pixie.cli.analyze_command — deterministic analysis generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pixie.cli.analyze_command import (
    _build_cross_dataset_summary,
    _build_dataset_summary,
    _evaluator_stats,
    _failure_clusters,
    _load_full_trace,
    analyze,
)
from pixie.harness.run_result import (
    DatasetResult,
    EntryResult,
    EvaluationResult,
    RunResult,
    save_test_result,
)


def _make_result(tmp_path: Path) -> RunResult:
    """Create and save a sample result for testing."""
    result = RunResult(
        test_id="20260403-120000",
        command="pixie test foo.json",
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
                        description="Basic arithmetic",
                        evaluations=[
                            EvaluationResult(
                                evaluator="Factuality",
                                score=1.0,
                                reasoning="Correct",
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
                                reasoning="Incorrect — said London not Paris",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
    save_test_result(result)
    return result


def _make_multi_dataset_result(tmp_path: Path) -> RunResult:
    """Create a result with two datasets for cross-dataset testing."""
    result = RunResult(
        test_id="20260403-130000",
        command="pixie test dir/",
        started_at="2026-04-03T13:00:00Z",
        ended_at="2026-04-03T13:00:10Z",
        datasets=[
            DatasetResult(
                dataset="ds-a",
                entries=[
                    EntryResult(
                        input="q1",
                        output="a1",
                        expected_output="a1",
                        description="Passes",
                        evaluations=[
                            EvaluationResult(
                                evaluator="Factuality", score=1.0, reasoning="OK"
                            ),
                        ],
                    ),
                ],
            ),
            DatasetResult(
                dataset="ds-b",
                entries=[
                    EntryResult(
                        input="q2",
                        output="wrong",
                        expected_output="right",
                        description="Fails",
                        evaluations=[
                            EvaluationResult(
                                evaluator="Factuality",
                                score=0.2,
                                reasoning="Bad",
                            ),
                            EvaluationResult(
                                evaluator="Tone",
                                score=0.3,
                                reasoning="Off",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
    save_test_result(result)
    return result


class TestEvaluatorStats:
    """Tests for _evaluator_stats()."""

    def test_single_evaluator(self) -> None:
        ds = DatasetResult(
            dataset="test",
            entries=[
                EntryResult(
                    input="q",
                    output="a",
                    expected_output=None,
                    description=None,
                    evaluations=[
                        EvaluationResult(
                            evaluator="Factuality", score=0.8, reasoning="Good"
                        ),
                    ],
                ),
                EntryResult(
                    input="q2",
                    output="a2",
                    expected_output=None,
                    description=None,
                    evaluations=[
                        EvaluationResult(
                            evaluator="Factuality", score=0.3, reasoning="Bad"
                        ),
                    ],
                ),
            ],
        )
        stats = _evaluator_stats(ds)
        assert "Factuality" in stats
        assert stats["Factuality"]["pass_rate"] == 50.0
        assert stats["Factuality"]["min"] == 0.3
        assert stats["Factuality"]["max"] == 0.8

    def test_empty_dataset(self) -> None:
        ds = DatasetResult(dataset="empty", entries=[])
        stats = _evaluator_stats(ds)
        assert stats == {}


class TestFailureClusters:
    """Tests for _failure_clusters()."""

    def test_groups_by_failed_evaluators(self) -> None:
        ds = DatasetResult(
            dataset="test",
            entries=[
                EntryResult(
                    input="q1",
                    output="a1",
                    expected_output=None,
                    description="entry0",
                    evaluations=[
                        EvaluationResult(
                            evaluator="A", score=0.2, reasoning="fail"
                        ),
                        EvaluationResult(
                            evaluator="B", score=0.1, reasoning="fail"
                        ),
                    ],
                ),
                EntryResult(
                    input="q2",
                    output="a2",
                    expected_output=None,
                    description="entry1",
                    evaluations=[
                        EvaluationResult(
                            evaluator="A", score=0.3, reasoning="fail"
                        ),
                        EvaluationResult(
                            evaluator="B", score=0.8, reasoning="pass"
                        ),
                    ],
                ),
            ],
        )
        clusters = _failure_clusters(ds)
        assert "A, B" in clusters
        assert len(clusters["A, B"]) == 1
        assert "A" in clusters
        assert len(clusters["A"]) == 1

    def test_no_failures(self) -> None:
        ds = DatasetResult(
            dataset="test",
            entries=[
                EntryResult(
                    input="q",
                    output="a",
                    expected_output=None,
                    description=None,
                    evaluations=[
                        EvaluationResult(
                            evaluator="A", score=1.0, reasoning="pass"
                        ),
                    ],
                ),
            ],
        )
        clusters = _failure_clusters(ds)
        assert clusters == {}


class TestBuildDatasetSummary:
    """Tests for _build_dataset_summary()."""

    def test_includes_overview(self, tmp_path: Path) -> None:
        ds = DatasetResult(
            dataset="my-dataset",
            entries=[
                EntryResult(
                    input="hi",
                    output="hello",
                    expected_output=None,
                    description="Greeting test",
                    evaluations=[
                        EvaluationResult(
                            evaluator="Factuality", score=1.0, reasoning="OK"
                        ),
                    ],
                ),
            ],
        )
        md = _build_dataset_summary(ds, str(tmp_path))
        assert "# Dataset: my-dataset" in md
        assert "1 passed" in md
        assert "100.0%" in md

    def test_includes_failure_clusters(self, tmp_path: Path) -> None:
        ds = DatasetResult(
            dataset="test",
            entries=[
                EntryResult(
                    input="q",
                    output="wrong",
                    expected_output="right",
                    description=None,
                    evaluations=[
                        EvaluationResult(
                            evaluator="ExactMatch",
                            score=0.0,
                            reasoning="No match",
                        ),
                    ],
                ),
            ],
        )
        md = _build_dataset_summary(ds, str(tmp_path))
        assert "Failure Clusters" in md
        assert "ExactMatch" in md

    def test_includes_stats_table(self, tmp_path: Path) -> None:
        ds = DatasetResult(
            dataset="test",
            entries=[
                EntryResult(
                    input="q",
                    output="a",
                    expected_output=None,
                    description=None,
                    evaluations=[
                        EvaluationResult(
                            evaluator="Factuality", score=0.8, reasoning="Good"
                        ),
                    ],
                ),
            ],
        )
        md = _build_dataset_summary(ds, str(tmp_path))
        assert "Per-Evaluator Statistics" in md
        assert "Factuality" in md

    def test_includes_trace_summary_when_traces_exist(
        self, tmp_path: Path
    ) -> None:
        # Create a trace file
        traces_dir = tmp_path / "traces"
        traces_dir.mkdir()
        trace_record = {
            "type": "llm_span_trace",
            "request_model": "gpt-4o",
            "input_tokens": 100,
            "output_tokens": 50,
            "duration_ms": 500.0,
        }
        (traces_dir / "entry-0.jsonl").write_text(
            json.dumps(trace_record) + "\n"
        )

        ds = DatasetResult(
            dataset="test",
            entries=[
                EntryResult(
                    input="q",
                    output="a",
                    expected_output=None,
                    description=None,
                    evaluations=[
                        EvaluationResult(
                            evaluator="F", score=1.0, reasoning="ok"
                        ),
                    ],
                    trace_file="traces/entry-0.jsonl",
                ),
            ],
        )
        md = _build_dataset_summary(ds, str(tmp_path))
        assert "Trace Summary" in md
        assert "gpt-4o" in md
        assert "100" in md

    def test_omits_trace_section_without_traces(self, tmp_path: Path) -> None:
        ds = DatasetResult(
            dataset="test",
            entries=[
                EntryResult(
                    input="q",
                    output="a",
                    expected_output=None,
                    description=None,
                    evaluations=[
                        EvaluationResult(
                            evaluator="F", score=1.0, reasoning="ok"
                        ),
                    ],
                ),
            ],
        )
        md = _build_dataset_summary(ds, str(tmp_path))
        assert "Trace Summary" not in md


class TestBuildCrossDatasetSummary:
    """Tests for _build_cross_dataset_summary()."""

    def test_aggregate_stats(self, tmp_path: Path) -> None:
        result = RunResult(
            test_id="test",
            command="pixie test",
            started_at="",
            ended_at="",
            datasets=[
                DatasetResult(
                    dataset="a",
                    entries=[
                        EntryResult(
                            input="q",
                            output="a",
                            expected_output=None,
                            description=None,
                            evaluations=[
                                EvaluationResult(
                                    evaluator="F", score=1.0, reasoning="ok"
                                ),
                            ],
                        ),
                    ],
                ),
                DatasetResult(
                    dataset="b",
                    entries=[
                        EntryResult(
                            input="q",
                            output="a",
                            expected_output=None,
                            description=None,
                            evaluations=[
                                EvaluationResult(
                                    evaluator="F", score=0.2, reasoning="bad"
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        md = _build_cross_dataset_summary(result, str(tmp_path))
        assert "Cross-Dataset Summary" in md
        assert "2 dataset(s)" in md
        assert "50.0%" in md
        assert "Evaluator Consistency" in md


class TestAnalyzeCommand:
    """Tests for the analyze() entry point."""

    def test_missing_test_id(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        result = analyze(test_id="nonexistent")
        assert result == 1

    def test_analyze_creates_dataset_md(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        _make_result(tmp_path)

        result = analyze(test_id="20260403-120000")
        assert result == 0

        analysis_path = tmp_path / "results" / "20260403-120000" / "dataset-0.md"
        assert analysis_path.exists()
        content = analysis_path.read_text()
        assert "sample-qa" in content
        assert "Factuality" in content
        assert "Failure Clusters" in content

    def test_analyze_creates_summary_md(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        _make_multi_dataset_result(tmp_path)

        result = analyze(test_id="20260403-130000")
        assert result == 0

        summary_path = tmp_path / "results" / "20260403-130000" / "summary.md"
        assert summary_path.exists()
        content = summary_path.read_text()
        assert "Cross-Dataset Summary" in content
        assert "2 dataset(s)" in content

    def test_analyze_no_openai_needed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify analyze works without OPENAI_API_KEY."""
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        _make_result(tmp_path)

        result = analyze(test_id="20260403-120000")
        assert result == 0

    def test_analyze_with_trace_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        result_obj = RunResult(
            test_id="20260403-140000",
            command="pixie test",
            started_at="2026-04-03T14:00:00Z",
            ended_at="2026-04-03T14:00:05Z",
            datasets=[
                DatasetResult(
                    dataset="traced",
                    entries=[
                        EntryResult(
                            input="q",
                            output="a",
                            expected_output=None,
                            description="Traced entry",
                            evaluations=[
                                EvaluationResult(
                                    evaluator="F", score=1.0, reasoning="ok"
                                ),
                            ],
                            trace_file="traces/entry-0.jsonl",
                        ),
                    ],
                ),
            ],
        )
        save_test_result(result_obj)

        # Create trace file
        result_dir = tmp_path / "results" / "20260403-140000"
        traces_dir = result_dir / "traces"
        traces_dir.mkdir(parents=True, exist_ok=True)
        trace_record = {
            "type": "llm_span_trace",
            "request_model": "gpt-4o",
            "input_tokens": 100,
            "output_tokens": 50,
            "duration_ms": 500.0,
        }
        (traces_dir / "entry-0.jsonl").write_text(
            json.dumps(trace_record) + "\n"
        )

        exit_code = analyze(test_id="20260403-140000")
        assert exit_code == 0

        analysis = (result_dir / "dataset-0.md").read_text()
        assert "Trace Summary" in analysis
        assert "gpt-4o" in analysis

    def test_load_full_trace_mixed_records(self, tmp_path: Path) -> None:
        """_load_full_trace returns kwargs, wrap, and llm_span_trace records."""
        traces_dir = tmp_path / "traces"
        traces_dir.mkdir()
        records = [
            {"type": "kwargs", "value": {"msg": "hi"}},
            {"type": "wrap", "name": "input_data", "purpose": "input"},
            {"type": "llm_span_trace", "request_model": "gpt-4o"},
            {"type": "wrap", "name": "result", "purpose": "output"},
        ]
        (traces_dir / "entry-0.jsonl").write_text(
            "\n".join(json.dumps(r) for r in records) + "\n"
        )
        entry = EntryResult(
            input="q",
            output="a",
            expected_output=None,
            description=None,
            evaluations=[],
            trace_file="traces/entry-0.jsonl",
        )
        loaded = _load_full_trace(str(tmp_path), entry)
        assert len(loaded) == 4
        assert loaded[0]["type"] == "kwargs"
        assert loaded[1]["type"] == "wrap"
        assert loaded[2]["type"] == "llm_span_trace"
        assert loaded[3]["type"] == "wrap"

    def test_entry_details_shows_wrap_events(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Entry details section shows wrap events alongside LLM calls."""
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        result_dir = tmp_path / "results" / "20260403-150000"
        traces_dir = result_dir / "traces"
        traces_dir.mkdir(parents=True, exist_ok=True)
        records = [
            {"type": "kwargs", "value": {"msg": "hi"}},
            {"type": "wrap", "name": "input_data", "purpose": "input",
             "captured_at": "2026-04-03T15:00:00Z"},
            {"type": "llm_span_trace", "request_model": "gpt-4o",
             "input_tokens": 50, "output_tokens": 25, "duration_ms": 200.0},
        ]
        (traces_dir / "entry-0.jsonl").write_text(
            "\n".join(json.dumps(r) for r in records) + "\n"
        )
        ds = DatasetResult(
            dataset="test",
            entries=[
                EntryResult(
                    input="q",
                    output="a",
                    expected_output=None,
                    description="Traced entry",
                    evaluations=[
                        EvaluationResult(
                            evaluator="F", score=1.0, reasoning="ok"
                        ),
                    ],
                    trace_file="traces/entry-0.jsonl",
                ),
            ],
        )
        md = _build_dataset_summary(ds, str(result_dir))
        assert "wrap(input)" in md
        assert "input_data" in md
        assert "llm" in md
        assert "gpt-4o" in md
