"""Tests for pixie.web.watcher — file watching utilities."""

from __future__ import annotations

from pathlib import Path

from watchfiles import Change

from pixie.web.watcher import _change_label, _is_artifact


class TestIsArtifact:
    def test_top_level_md_is_artifact(self, tmp_path: Path) -> None:
        path = tmp_path / "01-entry.md"
        assert _is_artifact(path, tmp_path)

    def test_top_level_json_is_artifact(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        assert _is_artifact(path, tmp_path)

    def test_top_level_jsonl_is_artifact(self, tmp_path: Path) -> None:
        path = tmp_path / "data.jsonl"
        assert _is_artifact(path, tmp_path)

    def test_top_level_py_is_artifact(self, tmp_path: Path) -> None:
        path = tmp_path / "evaluator.py"
        assert _is_artifact(path, tmp_path)

    def test_top_level_init_py_is_not_artifact(self, tmp_path: Path) -> None:
        path = tmp_path / "__init__.py"
        assert not _is_artifact(path, tmp_path)

    def test_dataset_json_is_artifact(self, tmp_path: Path) -> None:
        path = tmp_path / "datasets" / "faq.json"
        assert _is_artifact(path, tmp_path)

    def test_scorecard_html_is_artifact(self, tmp_path: Path) -> None:
        path = tmp_path / "scorecards" / "test.html"
        assert _is_artifact(path, tmp_path)

    def test_txt_file_is_not_artifact(self, tmp_path: Path) -> None:
        path = tmp_path / "test.txt"
        assert not _is_artifact(path, tmp_path)

    def test_nested_md_is_not_artifact(self, tmp_path: Path) -> None:
        path = tmp_path / "subdir" / "nested.md"
        assert not _is_artifact(path, tmp_path)

    def test_non_dataset_json_is_not_artifact(self, tmp_path: Path) -> None:
        path = tmp_path / "other" / "config.json"
        assert not _is_artifact(path, tmp_path)

    def test_result_json_is_artifact(self, tmp_path: Path) -> None:
        path = tmp_path / "results" / "20260403-120000" / "result.json"
        assert _is_artifact(path, tmp_path)

    def test_result_analysis_md_is_artifact(self, tmp_path: Path) -> None:
        path = tmp_path / "results" / "20260403-120000" / "dataset-0.md"
        assert _is_artifact(path, tmp_path)

    def test_result_other_file_not_artifact(self, tmp_path: Path) -> None:
        path = tmp_path / "results" / "20260403-120000" / "data.py"
        assert not _is_artifact(path, tmp_path)


class TestChangeLabel:
    def test_added(self) -> None:
        assert _change_label(Change.added) == "added"

    def test_modified(self) -> None:
        assert _change_label(Change.modified) == "modified"

    def test_deleted(self) -> None:
        assert _change_label(Change.deleted) == "deleted"
