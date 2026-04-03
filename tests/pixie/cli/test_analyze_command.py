"""Tests for pixie.cli.analyze_command — analysis generation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from pixie.cli.analyze_command import _build_analysis_prompt, analyze
from pixie.evals.test_result import (
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
                                reasoning="Incorrect",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
    save_test_result(result)
    return result


class TestBuildAnalysisPrompt:
    """Tests for _build_analysis_prompt()."""

    def test_includes_dataset_name(self) -> None:
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
        prompt = _build_analysis_prompt(ds)
        assert "my-dataset" in prompt
        assert "1/1 entries passed" in prompt

    def test_includes_failing_entry(self) -> None:
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
                            evaluator="ExactMatch", score=0.0, reasoning="No match"
                        ),
                    ],
                ),
            ],
        )
        prompt = _build_analysis_prompt(ds)
        assert "FAIL" in prompt
        assert "ExactMatch" in prompt
        assert "0/1 entries passed" in prompt


class TestAnalyzeCommand:
    """Tests for the analyze() entry point."""

    def test_missing_test_id(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        result = analyze(test_id="nonexistent")
        assert result == 1

    def test_analyze_calls_openai(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path))
        _make_result(tmp_path)

        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(message=AsyncMock(content="## Analysis\nAll good."))
        ]
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("openai.AsyncOpenAI", return_value=mock_client):
            result = analyze(test_id="20260403-120000")

        assert result == 0
        analysis_path = tmp_path / "results" / "20260403-120000" / "dataset-0.md"
        assert analysis_path.exists()
        assert "Analysis" in analysis_path.read_text()
