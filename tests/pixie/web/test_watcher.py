"""Tests for pixie.web.watcher — file watching utilities."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from watchfiles import Change

from pixie.web import watcher
from pixie.web.app import SSEManager
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

    def test_result_deep_evaluations_jsonl_is_artifact(self, tmp_path: Path) -> None:
        path = (
            tmp_path
            / "results"
            / "20260403-120000"
            / "dataset-0"
            / "entry-0"
            / "evaluations.jsonl"
        )
        assert _is_artifact(path, tmp_path)

    def test_result_deep_analysis_md_is_artifact(self, tmp_path: Path) -> None:
        path = (
            tmp_path
            / "results"
            / "20260403-120000"
            / "dataset-0"
            / "entry-0"
            / "analysis.md"
        )
        assert _is_artifact(path, tmp_path)

    def test_result_deep_config_json_is_artifact(self, tmp_path: Path) -> None:
        path = (
            tmp_path
            / "results"
            / "20260403-120000"
            / "dataset-0"
            / "entry-0"
            / "config.json"
        )
        assert _is_artifact(path, tmp_path)

    def test_result_action_plan_md_is_artifact(self, tmp_path: Path) -> None:
        path = tmp_path / "results" / "20260403-120000" / "action-plan.md"
        assert _is_artifact(path, tmp_path)

    def test_result_dataset_metadata_json_is_artifact(self, tmp_path: Path) -> None:
        path = tmp_path / "results" / "20260403-120000" / "dataset-0" / "metadata.json"
        assert _is_artifact(path, tmp_path)

    def test_result_deep_py_not_artifact(self, tmp_path: Path) -> None:
        path = (
            tmp_path
            / "results"
            / "20260403-120000"
            / "dataset-0"
            / "entry-0"
            / "script.py"
        )
        assert not _is_artifact(path, tmp_path)


class TestChangeLabel:
    def test_added(self) -> None:
        assert _change_label(Change.added) == "added"

    def test_modified(self) -> None:
        assert _change_label(Change.modified) == "modified"

    def test_deleted(self) -> None:
        assert _change_label(Change.deleted) == "deleted"


class RecordingSSE(SSEManager):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[tuple[str, object]] = []

    async def broadcast(self, event_type: str, data: object) -> None:
        self.events.append((event_type, data))


class TestWatchArtifacts:
    @pytest.mark.asyncio
    async def test_emits_single_telemetry_event_for_result_batch(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        result_meta = tmp_path / "results" / "run-1" / "meta.json"
        result_analysis = tmp_path / "results" / "run-1" / "dataset-0" / "analysis.md"
        dataset_file = tmp_path / "datasets" / "faq.json"
        manifest = {"results": [{"name": "run-1", "path": "results/run-1"}]}
        sse = RecordingSSE()
        emitted: list[tuple[str, dict[str, str]]] = []

        async def fake_awatch(_root: Path) -> AsyncIterator[list[tuple[Change, str]]]:
            yield [
                (Change.added, str(result_meta)),
                (Change.added, str(result_analysis)),
                (Change.modified, str(dataset_file)),
            ]

        monkeypatch.setattr(watcher, "awatch", fake_awatch)
        monkeypatch.setattr(watcher, "__version__", "1.2.3", raising=False)
        monkeypatch.setattr(
            watcher,
            "emit",
            lambda event, properties: emitted.append((event, properties)),
        )
        monkeypatch.setattr(watcher, "_build_manifest", lambda _root: manifest)

        await watcher.watch_artifacts(str(tmp_path), sse)

        assert emitted == [("pixie_artifact_created", {"version": "1.2.3"})]
        assert sse.events == [
            (
                "file_change",
                [
                    {"type": "added", "path": "results/run-1/meta.json"},
                    {
                        "type": "added",
                        "path": "results/run-1/dataset-0/analysis.md",
                    },
                    {"type": "modified", "path": "datasets/faq.json"},
                ],
            ),
            ("manifest", manifest),
        ]

    @pytest.mark.asyncio
    async def test_does_not_emit_telemetry_for_modified_result_only(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        result_meta = tmp_path / "results" / "run-1" / "meta.json"
        sse = RecordingSSE()
        emitted: list[tuple[str, dict[str, str]]] = []

        async def fake_awatch(_root: Path) -> AsyncIterator[list[tuple[Change, str]]]:
            yield [(Change.modified, str(result_meta))]

        monkeypatch.setattr(watcher, "awatch", fake_awatch)
        monkeypatch.setattr(
            watcher,
            "emit",
            lambda event, properties: emitted.append((event, properties)),
        )
        monkeypatch.setattr(watcher, "_build_manifest", lambda _root: {"results": []})

        await watcher.watch_artifacts(str(tmp_path), sse)

        assert emitted == []
        assert sse.events[0][0] == "file_change"
        assert sse.events[1] == ("manifest", {"results": []})
