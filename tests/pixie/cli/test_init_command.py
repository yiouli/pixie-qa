"""Tests for ``pixie init`` command — directory scaffolding."""

from __future__ import annotations

from pathlib import Path

import pytest

from pixie.cli.init_command import init_pixie_dir


class TestInitPixieDir:
    """Tests for the init_pixie_dir function."""

    def test_creates_root_and_subdirs(self, tmp_path: Path) -> None:
        root = tmp_path / "pixie_qa"
        result = init_pixie_dir(str(root))

        assert result == root
        assert root.is_dir()
        assert (root / "datasets").is_dir()
        assert (root / "tests").is_dir()
        assert (root / "scripts").is_dir()

    def test_creates_memory_md(self, tmp_path: Path) -> None:
        root = tmp_path / "pixie_qa"
        init_pixie_dir(str(root))

        memory = root / "MEMORY.md"
        assert memory.is_file()
        content = memory.read_text()
        assert "# Eval Notes" in content

    def test_does_not_overwrite_existing_memory(self, tmp_path: Path) -> None:
        root = tmp_path / "pixie_qa"
        root.mkdir()
        memory = root / "MEMORY.md"
        memory.write_text("# My custom notes\n")

        init_pixie_dir(str(root))

        assert memory.read_text() == "# My custom notes\n"

    def test_idempotent_on_existing_structure(self, tmp_path: Path) -> None:
        root = tmp_path / "pixie_qa"
        init_pixie_dir(str(root))

        # Add a file inside a subdir
        (root / "datasets" / "sample.json").write_text("{}")

        # Re-run should not remove anything
        init_pixie_dir(str(root))

        assert (root / "datasets" / "sample.json").is_file()
        assert (root / "tests").is_dir()
        assert (root / "scripts").is_dir()

    def test_uses_config_default_when_no_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path / "custom_root"))

        result = init_pixie_dir()

        assert result == tmp_path / "custom_root"
        assert (tmp_path / "custom_root" / "datasets").is_dir()

    def test_nested_root_creates_parents(self, tmp_path: Path) -> None:
        root = tmp_path / "deep" / "nested" / "pixie_qa"
        init_pixie_dir(str(root))

        assert root.is_dir()
        assert (root / "tests").is_dir()
