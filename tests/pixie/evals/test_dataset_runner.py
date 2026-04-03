"""Tests for the dataset-driven test runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pixie.evals.dataset_runner import (
    BUILTIN_EVALUATOR_NAMES,
    _noop_runnable,
    _resolve_evaluator,
    _short_name,
    discover_dataset_files,
    load_dataset_entries,
    resolve_evaluator_name,
)

# ---------------------------------------------------------------------------
# resolve_evaluator_name
# ---------------------------------------------------------------------------


class TestResolveEvaluatorName:
    """Tests for evaluator name resolution."""

    def test_builtin_name_resolved(self) -> None:
        assert resolve_evaluator_name("Factuality") == "pixie.Factuality"

    def test_builtin_exact_match_resolved(self) -> None:
        assert resolve_evaluator_name("ExactMatch") == "pixie.ExactMatch"

    def test_fqn_passed_through(self) -> None:
        assert resolve_evaluator_name("myapp.evals.Custom") == "myapp.evals.Custom"

    def test_unknown_bare_name_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown evaluator"):
            resolve_evaluator_name("NotARealEvaluator")

    def test_whitespace_stripped(self) -> None:
        assert resolve_evaluator_name("  Factuality  ") == "pixie.Factuality"

    def test_all_builtins_recognized(self) -> None:
        for name in BUILTIN_EVALUATOR_NAMES:
            result = resolve_evaluator_name(name)
            assert result == f"pixie.{name}"


# ---------------------------------------------------------------------------
# _resolve_evaluator
# ---------------------------------------------------------------------------


class TestResolveEvaluator:
    """Tests for evaluator resolution and instantiation."""

    def test_resolve_builtin_by_short_name(self) -> None:
        evaluator = _resolve_evaluator("ExactMatch")
        assert hasattr(evaluator, "name")

    def test_resolve_builtin_by_fqn(self) -> None:
        evaluator = _resolve_evaluator("pixie.ExactMatch")
        assert hasattr(evaluator, "name")

    def test_resolve_with_whitespace(self) -> None:
        evaluator = _resolve_evaluator("  ExactMatch  ")
        assert hasattr(evaluator, "name")

    def test_invalid_fqn_raises(self) -> None:
        with pytest.raises((ImportError, ModuleNotFoundError)):
            _resolve_evaluator("nonexistent.module.Evaluator")

    def test_invalid_class_name_raises(self) -> None:
        with pytest.raises(AttributeError):
            _resolve_evaluator("pixie.NonexistentEvaluator")

    def test_unknown_bare_name_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown evaluator"):
            _resolve_evaluator("CompletelyMadeUp")


# ---------------------------------------------------------------------------
# _short_name
# ---------------------------------------------------------------------------


class TestShortName:
    """Tests for extracting short class names from FQNs."""

    def test_fully_qualified(self) -> None:
        assert _short_name("pixie.evals.scorers.Factuality") == "Factuality"

    def test_simple_fqn(self) -> None:
        assert _short_name("pixie.Factuality") == "Factuality"

    def test_bare_name(self) -> None:
        assert _short_name("Factuality") == "Factuality"


# ---------------------------------------------------------------------------
# _noop_runnable
# ---------------------------------------------------------------------------


class TestNoopRunnable:
    """Tests for the noop runnable."""

    @pytest.mark.asyncio
    async def test_noop_returns_none(self) -> None:
        await _noop_runnable({"question": "test"})  # should not raise


# ---------------------------------------------------------------------------
# discover_dataset_files
# ---------------------------------------------------------------------------


def _write_dataset(
    tmp_path: Path,
    name: str,
    items: list[dict[str, Any]],
) -> Path:
    """Helper: write a dataset JSON file and return its path."""
    dataset = {"name": name, "items": items}
    fpath = tmp_path / f"{name}.json"
    fpath.write_text(json.dumps(dataset), encoding="utf-8")
    return fpath


class TestDiscoverDatasetFiles:
    """Tests for discover_dataset_files."""

    def test_single_json_file(self, tmp_path: Path) -> None:
        fpath = _write_dataset(tmp_path, "ds", [])
        result = discover_dataset_files(str(fpath))
        assert result == [fpath]

    def test_directory_with_json_files(self, tmp_path: Path) -> None:
        _write_dataset(tmp_path, "a", [])
        _write_dataset(tmp_path, "b", [])
        result = discover_dataset_files(str(tmp_path))
        assert len(result) == 2

    def test_nested_directory(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        _write_dataset(sub, "nested", [])
        result = discover_dataset_files(str(tmp_path))
        assert len(result) == 1
        assert result[0].name == "nested.json"

    def test_empty_directory(self, tmp_path: Path) -> None:
        result = discover_dataset_files(str(tmp_path))
        assert result == []

    def test_nonexistent_path(self, tmp_path: Path) -> None:
        result = discover_dataset_files(str(tmp_path / "nope"))
        assert result == []


# ---------------------------------------------------------------------------
# load_dataset_entries
# ---------------------------------------------------------------------------


class TestLoadDatasetEntries:
    """Tests for load_dataset_entries."""

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Dataset not found"):
            load_dataset_entries(tmp_path / "missing.json")

    def test_empty_dataset(self, tmp_path: Path) -> None:
        fpath = _write_dataset(tmp_path, "empty", [])
        name, entries = load_dataset_entries(fpath)
        assert name == "empty"
        assert entries == []

    def test_items_without_evaluators_skipped(self, tmp_path: Path) -> None:
        items = [
            {
                "eval_input": "Q1",
                "eval_output": "A1",
                "expected_output": "A1",
            }
        ]
        fpath = _write_dataset(tmp_path, "no-evals", items)
        _, entries = load_dataset_entries(fpath)
        assert entries == []

    def test_evaluators_as_json_array(self, tmp_path: Path) -> None:
        items = [
            {
                "eval_input": "Q1",
                "eval_output": "A1",
                "expected_output": "A1",
                "evaluators": ["ExactMatch"],
            },
        ]
        fpath = _write_dataset(tmp_path, "array-evals", items)
        _, entries = load_dataset_entries(fpath)
        assert len(entries) == 1
        _, eval_names = entries[0]
        assert eval_names == ["ExactMatch"]

    def test_multiple_evaluators_per_row(self, tmp_path: Path) -> None:
        items = [
            {
                "eval_input": "Q1",
                "eval_output": "A1",
                "expected_output": "A1",
                "evaluators": ["ExactMatch", "LevenshteinMatch"],
            },
        ]
        fpath = _write_dataset(tmp_path, "multi-eval", items)
        _, entries = load_dataset_entries(fpath)
        assert len(entries) == 1
        _, eval_names = entries[0]
        assert eval_names == ["ExactMatch", "LevenshteinMatch"]

    def test_different_evaluators_per_row(self, tmp_path: Path) -> None:
        items = [
            {
                "eval_input": "Q1",
                "eval_output": "A1",
                "expected_output": "A1",
                "evaluators": ["ExactMatch"],
            },
            {
                "eval_input": "Q2",
                "eval_output": "A2",
                "expected_output": "A2",
                "evaluators": ["ExactMatch", "LevenshteinMatch"],
            },
        ]
        fpath = _write_dataset(tmp_path, "mixed-evals", items)
        _, entries = load_dataset_entries(fpath)
        assert len(entries) == 2
        assert len(entries[0][1]) == 1
        assert len(entries[1][1]) == 2

    def test_custom_fqn_evaluator(self, tmp_path: Path) -> None:
        items = [
            {
                "eval_input": "Q1",
                "eval_output": "A1",
                "evaluators": ["myapp.evals.Custom"],
            },
        ]
        fpath = _write_dataset(tmp_path, "custom", items)
        _, entries = load_dataset_entries(fpath)
        assert len(entries) == 1
        _, eval_names = entries[0]
        assert eval_names == ["myapp.evals.Custom"]

    def test_empty_evaluators_list_skipped(self, tmp_path: Path) -> None:
        items = [
            {
                "eval_input": "Q1",
                "eval_output": "A1",
                "evaluators": [],
            },
        ]
        fpath = _write_dataset(tmp_path, "empty-list", items)
        _, entries = load_dataset_entries(fpath)
        assert entries == []

    def test_uses_filename_stem_when_no_name(self, tmp_path: Path) -> None:
        data = {
            "items": [
                {
                    "eval_input": "Q1",
                    "eval_output": "A1",
                    "evaluators": ["ExactMatch"],
                }
            ]
        }
        fpath = tmp_path / "my-dataset.json"
        fpath.write_text(json.dumps(data), encoding="utf-8")
        name, entries = load_dataset_entries(fpath)
        assert name == "my-dataset"
        assert len(entries) == 1

    def test_mixed_items_with_and_without_evaluators(self, tmp_path: Path) -> None:
        items: list[dict[str, Any]] = [
            {
                "eval_input": "Q1",
                "eval_output": "A1",
                "expected_output": "A1",
                "evaluators": ["ExactMatch"],
            },
            {
                "eval_input": "Q2",
                "eval_output": "A2",
            },
        ]
        fpath = _write_dataset(tmp_path, "mixed", items)
        _, entries = load_dataset_entries(fpath)
        assert len(entries) == 1
