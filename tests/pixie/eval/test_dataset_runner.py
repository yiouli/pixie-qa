"""Tests for the dataset-driven test runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pixie.harness.runner import (
    _expand_evaluator_names,
    _load_callable,
    _noop_runnable,
    _resolve_evaluator,
    _short_name,
    discover_dataset_files,
    load_dataset,
    resolve_evaluator_name,
    resolve_runnable_reference,
)

# ---------------------------------------------------------------------------
# resolve_evaluator_name / _resolve_evaluator
# ---------------------------------------------------------------------------


class TestResolveEvaluatorName:
    def test_builtin_name_resolved(self) -> None:
        assert resolve_evaluator_name("Factuality") == "pixie.Factuality"

    def test_filepath_reference_passed_through(self) -> None:
        ref = "pixie_qa/evaluators.py:Custom"
        assert resolve_evaluator_name(ref) == ref

    def test_unknown_bare_name_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown evaluator"):
            resolve_evaluator_name("NotARealEvaluator")


class TestResolveEvaluator:
    def test_resolve_builtin_by_short_name(self) -> None:
        evaluator = _resolve_evaluator("ExactMatch")
        assert hasattr(evaluator, "name")

    def test_unknown_bare_name_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown evaluator"):
            _resolve_evaluator("NonexistentEvaluator")

    def test_resolve_function_evaluator(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A module-level function should be returned as-is, not called."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "func_eval.py").write_text(
            "from pixie.eval.evaluation import Evaluation\n"
            "from pixie.eval.evaluable import Evaluable\n"
            "\n"
            "def my_func_eval(evaluable: Evaluable, *, trace=None) -> Evaluation:\n"
            "    return Evaluation(score=1.0, reasoning='ok')\n"
        )
        result = _resolve_evaluator("func_eval.py:my_func_eval")
        assert callable(result)
        assert result.__name__ == "my_func_eval"

    def test_resolve_prebuilt_instance(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A module-level callable instance should be returned as-is."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "inst_eval.py").write_text(
            "from pixie.eval.evaluation import Evaluation\n"
            "from pixie.eval.evaluable import Evaluable\n"
            "\n"
            "class _Inner:\n"
            "    def __call__(self, evaluable: Evaluable, *, trace=None) -> Evaluation:\n"
            "        return Evaluation(score=1.0, reasoning='ok')\n"
            "\n"
            "my_instance = _Inner()\n"
        )
        result = _resolve_evaluator("inst_eval.py:my_instance")
        assert callable(result)
        assert type(result).__name__ == "_Inner"


# ---------------------------------------------------------------------------
# resolve_runnable_reference / _short_name / _noop_runnable
# ---------------------------------------------------------------------------


class TestLoadCallable:
    def test_loads_function(self, tmp_path: Path) -> None:
        (tmp_path / "mymod.py").write_text("def greet(x): return f'hi {x}'\n")
        func = _load_callable("mymod.py:greet", tmp_path)
        assert func("world") == "hi world"

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Module file not found"):
            _load_callable("nope.py:func", tmp_path)

    def test_missing_attr_raises(self, tmp_path: Path) -> None:
        (tmp_path / "empty.py").write_text("x = 1\n")
        with pytest.raises(AttributeError):
            _load_callable("empty.py:missing", tmp_path)

    def test_no_colon_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="filepath:name"):
            _load_callable("nocolon", tmp_path)


class TestResolveRunnable:
    def test_resolves_filepath_reference(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "run.py").write_text("def my_func(x): return str(x)\n")
        func = resolve_runnable_reference("run.py:my_func")
        assert callable(func)

    def test_no_colon_raises(self) -> None:
        with pytest.raises(ValueError, match="filepath:name"):
            resolve_runnable_reference("json.dumps")


class TestShortName:
    def test_fully_qualified(self) -> None:
        assert _short_name("pixie.eval.scorers.Factuality") == "Factuality"

    def test_filepath_reference(self) -> None:
        assert _short_name("pixie_qa/evaluators.py:ConciseStyle") == "ConciseStyle"


class TestNoopRunnable:
    @pytest.mark.asyncio
    async def test_noop_returns_none(self) -> None:
        await _noop_runnable({"question": "test"})


# ---------------------------------------------------------------------------
# dataset discovery
# ---------------------------------------------------------------------------


def _write_runnable(tmp_path: Path) -> str:
    """Write a minimal runnable file and return ``filepath:name`` reference."""
    fpath = tmp_path / "_test_runnable.py"
    fpath.write_text("def run(x):\n    return str(x)\n")
    return "_test_runnable.py:run"


def _make_entry(
    *,
    inp: str = "Q1",
    expectation: str | None = None,
    description: str = "desc",
    evaluators: list[str] | None = None,
    entry_kwargs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a single dataset entry in the new nested format."""
    test_case: dict[str, Any] = {
        "eval_input": [{"name": "input", "value": inp}],
        "description": description,
    }
    if expectation is not None:
        test_case["expectation"] = expectation
    entry: dict[str, Any] = {
        "entry_kwargs": entry_kwargs or {"question": inp},
        "test_case": test_case,
    }
    if evaluators is not None:
        entry["evaluators"] = evaluators
    return entry


def _write_dataset(
    tmp_path: Path,
    name: str,
    entries: list[dict[str, Any]],
    *,
    runnable: str | None = None,
    evaluators: list[str] | None = None,
) -> Path:
    if runnable is None:
        runnable = _write_runnable(tmp_path)
    dataset: dict[str, Any] = {
        "name": name,
        "runnable": runnable,
        "entries": entries,
    }
    if evaluators is not None:
        dataset["evaluators"] = evaluators
    fpath = tmp_path / f"{name}.json"
    fpath.write_text(json.dumps(dataset), encoding="utf-8")
    return fpath


class TestDiscoverDatasetFiles:
    def test_single_json_file(self, tmp_path: Path) -> None:
        fpath = _write_dataset(tmp_path, "ds", [])
        result = discover_dataset_files(str(fpath))
        assert result == [fpath]

    def test_directory_with_json_files(self, tmp_path: Path) -> None:
        _write_dataset(tmp_path, "a", [])
        _write_dataset(tmp_path, "b", [])
        result = discover_dataset_files(str(tmp_path))
        assert len(result) == 2


# ---------------------------------------------------------------------------
# evaluator expansion
# ---------------------------------------------------------------------------


class TestExpandEvaluatorNames:
    def test_none_row_uses_defaults(self) -> None:
        result = _expand_evaluator_names(None, ["ExactMatch", "Factuality"])
        assert result == ["ExactMatch", "Factuality"]

    def test_row_overrides_defaults(self) -> None:
        result = _expand_evaluator_names(["LevenshteinMatch"], ["ExactMatch"])
        assert result == ["LevenshteinMatch"]

    def test_ellipsis_expands_defaults(self) -> None:
        result = _expand_evaluator_names(["...", "LevenshteinMatch"], ["ExactMatch"])
        assert result == ["ExactMatch", "LevenshteinMatch"]


# ---------------------------------------------------------------------------
# load_dataset
# ---------------------------------------------------------------------------


class TestLoadDataset:
    def test_loads_valid_dataset(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runnable_ref = _write_runnable(tmp_path)
        fpath = _write_dataset(
            tmp_path,
            "ok",
            [_make_entry(expectation="A1", evaluators=["ExactMatch"])],
            runnable=runnable_ref,
        )
        loaded = load_dataset(fpath)
        assert loaded.name == "ok"
        assert loaded.runnable == runnable_ref
        assert len(loaded.entries) == 1

    def test_row_ellipsis_expands_defaults(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        fpath = _write_dataset(
            tmp_path,
            "ellipsis",
            [_make_entry(evaluators=["...", "LevenshteinMatch"])],
            evaluators=["ExactMatch"],
        )
        loaded = load_dataset(fpath)
        assert loaded.entries[0].evaluators == ["ExactMatch", "LevenshteinMatch"]

    def test_defaults_used_when_row_evaluators_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        entry = _make_entry()  # no evaluators on the entry
        fpath = _write_dataset(
            tmp_path,
            "defaults",
            [entry],
            evaluators=["ExactMatch"],
        )
        loaded = load_dataset(fpath)
        assert loaded.entries[0].evaluators == ["ExactMatch"]

    def test_name_defaults_to_stem(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runnable_ref = _write_runnable(tmp_path)
        data: dict[str, Any] = {
            "runnable": runnable_ref,
            "entries": [_make_entry(evaluators=["ExactMatch"])],
        }
        fpath = tmp_path / "my-dataset.json"
        fpath.write_text(json.dumps(data), encoding="utf-8")
        loaded = load_dataset(fpath)
        assert loaded.name == "my-dataset"

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_dataset(tmp_path / "nonexistent.json")

    def test_missing_runnable_raises(self, tmp_path: Path) -> None:
        data = {
            "name": "bad",
            "entries": [_make_entry(evaluators=["ExactMatch"])],
        }
        fpath = tmp_path / "bad.json"
        fpath.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError, match="runnable"):
            load_dataset(fpath)

    def test_missing_description_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        entry = _make_entry(evaluators=["ExactMatch"])
        del entry["test_case"]["description"]
        fpath = _write_dataset(tmp_path, "bad-desc", [entry])
        with pytest.raises(ValueError, match="description"):
            load_dataset(fpath)

    def test_no_evaluators_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        entry = _make_entry()  # no evaluators at entry or dataset level
        fpath = _write_dataset(tmp_path, "bad-evals", [entry])
        with pytest.raises(ValueError, match="no evaluators resolved"):
            load_dataset(fpath)

    def test_invalid_runnable_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        fpath = _write_dataset(
            tmp_path,
            "bad-run",
            [_make_entry(evaluators=["ExactMatch"])],
            runnable="not_a_filepath",
        )
        with pytest.raises(ValueError, match="(?i)runnable|filepath:name"):
            load_dataset(fpath)

    def test_invalid_evaluator_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        fpath = _write_dataset(
            tmp_path,
            "bad-evaluator",
            [_make_entry(evaluators=["Nope"])],
        )
        with pytest.raises(ValueError, match="(?i)evaluator|Nope"):
            load_dataset(fpath)

    def test_non_dict_json_raises(self, tmp_path: Path) -> None:
        fpath = tmp_path / "bad.json"
        fpath.write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(ValueError, match="object"):
            load_dataset(fpath)
