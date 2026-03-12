"""Tests for pixie.evals.runner — test discovery and runner."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from pixie.evals.runner import (
    EvalTestResult,
    discover_tests,
    format_results,
    run_tests,
)

# ── Helpers ──────────────────────────────────────────────────────────────


def _write_test_file(tmp_path: Path, name: str, content: str) -> Path:
    """Write a Python test file with dedented content."""
    p = tmp_path / name
    p.write_text(textwrap.dedent(content))
    return p


# ── Test discovery tests ──────────────────────────────────────────────────


class TestDiscoverTests:
    """Tests for discover_tests()."""

    def test_finds_test_files_recursively(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        _write_test_file(
            tmp_path,
            "test_top.py",
            """\
            def test_a(): pass
        """,
        )
        _write_test_file(
            sub,
            "test_nested.py",
            """\
            def test_b(): pass
        """,
        )

        tests = discover_tests(str(tmp_path))
        names = {t.name for t in tests}
        assert "test_top.py::test_a" in names
        assert "test_nested.py::test_b" in names

    def test_finds_test_suffix_files(self, tmp_path: Path) -> None:
        _write_test_file(
            tmp_path,
            "my_test.py",
            """\
            def test_x(): pass
        """,
        )

        tests = discover_tests(str(tmp_path))
        assert len(tests) == 1
        assert "my_test.py::test_x" in tests[0].name

    def test_ignores_non_test_functions(self, tmp_path: Path) -> None:
        _write_test_file(
            tmp_path,
            "test_mod.py",
            """\
            def test_real(): pass
            def helper(): pass
            def setup(): pass
        """,
        )

        tests = discover_tests(str(tmp_path))
        names = {t.name for t in tests}
        assert len(names) == 1
        assert "test_mod.py::test_real" in names

    def test_ignores_non_test_files(self, tmp_path: Path) -> None:
        _write_test_file(
            tmp_path,
            "utils.py",
            """\
            def test_fake(): pass
        """,
        )

        tests = discover_tests(str(tmp_path))
        assert len(tests) == 0

    def test_discovers_async_test_functions(self, tmp_path: Path) -> None:
        _write_test_file(
            tmp_path,
            "test_async.py",
            """\
            async def test_async_fn(): pass
        """,
        )

        tests = discover_tests(str(tmp_path))
        assert len(tests) == 1
        assert tests[0].is_async

    def test_single_file_discovery(self, tmp_path: Path) -> None:
        f = _write_test_file(
            tmp_path,
            "test_single.py",
            """\
            def test_one(): pass
            def test_two(): pass
        """,
        )

        tests = discover_tests(str(f))
        assert len(tests) == 2


# ── Test runner tests ─────────────────────────────────────────────────────


class TestRunTests:
    """Tests for run_tests()."""

    def test_passes_for_normal_return(self, tmp_path: Path) -> None:
        _write_test_file(
            tmp_path,
            "test_ok.py",
            """\
            def test_pass():
                pass
        """,
        )

        results = run_tests(discover_tests(str(tmp_path)))
        assert len(results) == 1
        assert results[0].status == "passed"

    def test_runs_async_test_functions(self, tmp_path: Path) -> None:
        _write_test_file(
            tmp_path,
            "test_async.py",
            """\
            async def test_async_pass():
                pass
        """,
        )

        results = run_tests(discover_tests(str(tmp_path)))
        assert len(results) == 1
        assert results[0].status == "passed"

    def test_reports_fail_for_assertion_error(self, tmp_path: Path) -> None:
        _write_test_file(
            tmp_path,
            "test_fail.py",
            """\
            def test_fail():
                raise AssertionError("nope")
        """,
        )

        results = run_tests(discover_tests(str(tmp_path)))
        assert len(results) == 1
        assert results[0].status == "failed"
        assert "nope" in (results[0].message or "")

    def test_reports_error_for_other_exceptions(self, tmp_path: Path) -> None:
        _write_test_file(
            tmp_path,
            "test_err.py",
            """\
            def test_error():
                raise RuntimeError("boom")
        """,
        )

        results = run_tests(discover_tests(str(tmp_path)))
        assert len(results) == 1
        assert results[0].status == "error"
        assert "boom" in (results[0].message or "")

    def test_filter_by_name(self, tmp_path: Path) -> None:
        _write_test_file(
            tmp_path,
            "test_filter.py",
            """\
            def test_alpha(): pass
            def test_beta(): pass
        """,
        )

        tests = discover_tests(str(tmp_path), filter_pattern="alpha")
        assert len(tests) == 1
        assert "alpha" in tests[0].name

    def test_exit_code_zero_all_pass(self, tmp_path: Path) -> None:
        _write_test_file(
            tmp_path,
            "test_ok.py",
            """\
            def test_a(): pass
            def test_b(): pass
        """,
        )

        results = run_tests(discover_tests(str(tmp_path)))
        passed = all(r.status == "passed" for r in results)
        assert passed

    def test_exit_code_nonzero_on_failure(self, tmp_path: Path) -> None:
        _write_test_file(
            tmp_path,
            "test_mix.py",
            """\
            def test_ok(): pass
            def test_bad():
                raise AssertionError("fail")
        """,
        )

        results = run_tests(discover_tests(str(tmp_path)))
        has_failure = any(r.status != "passed" for r in results)
        assert has_failure

    def test_spans_isolated_between_tests(self, tmp_path: Path) -> None:
        """Each test should get a fresh trace handler."""
        _write_test_file(
            tmp_path,
            "test_iso.py",
            """\
            def test_first():
                pass
            def test_second():
                pass
        """,
        )

        results = run_tests(discover_tests(str(tmp_path)))
        assert all(r.status == "passed" for r in results)


# ── Import error propagation tests ──────────────────────────────────────


class TestDiscoverTestsImportErrors:
    """Tests for loud import error reporting in discover_tests()."""

    def test_import_error_propagates(self, tmp_path: Path) -> None:
        """Import errors must propagate, not silently skip."""
        _write_test_file(
            tmp_path,
            "test_bad.py",
            """\
            import nonexistent_package_xyz
            def test_never_reached(): pass
        """,
        )

        with pytest.raises(ModuleNotFoundError):
            discover_tests(str(tmp_path))

    def test_syntax_error_propagates(self, tmp_path: Path) -> None:
        """Syntax errors in test files must propagate."""
        p = tmp_path / "test_syntax.py"
        p.write_text("def test_broken(\n")

        with pytest.raises(SyntaxError):
            discover_tests(str(tmp_path))


# ── format_results tests ────────────────────────────────────────────────


class TestFormatResults:
    """Tests for format_results()."""

    def test_always_shows_error_message(self) -> None:
        """Error messages must appear even without verbose flag."""
        results = [
            EvalTestResult(name="test_a", status="error", message="Missing API key"),
        ]
        output = format_results(results, verbose=False)
        assert "Missing API key" in output

    def test_always_shows_failure_message(self) -> None:
        """Failure messages must appear even without verbose flag."""
        results = [
            EvalTestResult(name="test_b", status="failed", message="expected 1 got 2"),
        ]
        output = format_results(results, verbose=False)
        assert "expected 1 got 2" in output

    def test_verbose_shows_full_traceback(self) -> None:
        """Verbose mode shows all lines of multi-line message."""
        msg = "RuntimeError: boom\n  File test.py, line 1\n  in test_x"
        results = [
            EvalTestResult(name="test_c", status="error", message=msg),
        ]
        output = format_results(results, verbose=True)
        assert "RuntimeError: boom" in output
        assert "File test.py, line 1" in output
        assert "in test_x" in output

    def test_non_verbose_shows_first_line_only(self) -> None:
        """Non-verbose mode shows first line of multi-line message."""
        msg = "RuntimeError: boom\n  File test.py, line 1\n  in test_x"
        results = [
            EvalTestResult(name="test_c", status="error", message=msg),
        ]
        output = format_results(results, verbose=False)
        assert "RuntimeError: boom" in output
        assert "File test.py, line 1" not in output

    def test_passed_tests_show_checkmark(self) -> None:
        results = [EvalTestResult(name="test_ok", status="passed")]
        output = format_results(results)
        assert "\u2713" in output
        assert "1 passed" in output
