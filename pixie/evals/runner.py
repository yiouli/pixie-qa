"""Test discovery and runner for ``pixie test`` eval CLI.

Discovers test functions in ``test_*.py`` / ``*_test.py`` files, runs
them, and reports results.
"""

from __future__ import annotations

import asyncio
import importlib.util
import inspect
import sys
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


@dataclass(frozen=True)
class TestCase:
    """A discovered test function ready to execute.

    Attributes:
        name: Display name in ``file.py::function`` format.
        func: The test function (sync or async).
        is_async: Whether the function is a coroutine function.
    """

    name: str
    func: Callable[[], Any]
    is_async: bool


@dataclass(frozen=True)
class EvalTestResult:
    """Outcome of a single test execution.

    Attributes:
        name: The test name (``file.py::function``).
        status: ``'passed'``, ``'failed'``, or ``'error'``.
        message: Failure / error message, or None on pass.
    """

    name: str
    status: Literal["passed", "failed", "error"]
    message: str | None = None


def discover_tests(
    path: str,
    *,
    filter_pattern: str | None = None,
) -> list[TestCase]:
    """Discover eval test functions in *path*.

    Args:
        path: File or directory to search. If a directory, searches
            recursively for ``test_*.py`` and ``*_test.py`` files.
        filter_pattern: If provided, only include tests whose name
            contains this substring.

    Returns:
        List of ``TestCase`` objects sorted by name.

    Raises:
        ImportError: If a test file cannot be imported (syntax errors,
            missing dependencies, bad imports).  This ensures import
            failures are loud rather than silently producing "no tests
            collected".
    """
    target = Path(path)
    test_files: list[Path] = []

    if target.is_file():
        test_files.append(target)
    elif target.is_dir():
        for p in sorted(target.rglob("*.py")):
            if p.stem.startswith("test_") or p.stem.endswith("_test"):
                test_files.append(p)

    cases: list[TestCase] = []
    for fpath in test_files:
        module = _load_module(fpath)
        for attr_name in dir(module):
            if not attr_name.startswith("test_"):
                continue
            obj = getattr(module, attr_name)
            if not callable(obj):
                continue
            display_name = f"{fpath.name}::{attr_name}"
            is_async = inspect.iscoroutinefunction(obj)
            cases.append(TestCase(name=display_name, func=obj, is_async=is_async))

    if filter_pattern:
        cases = [c for c in cases if filter_pattern in c.name]

    cases.sort(key=lambda c: c.name)
    return cases


def _load_module(path: Path) -> Any:
    """Dynamically load a Python module from *path*.

    Raises:
        ImportError: If the module cannot be loaded (syntax errors,
            missing dependencies, etc.).  Errors propagate so callers
            see clear diagnostics instead of silent "no tests collected".
    """
    module_name = f"_pixie_test_{path.stem}_{id(path)}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    loader = spec.loader
    assert loader is not None  # guarded above
    loader.exec_module(module)
    return module


def run_tests(cases: list[TestCase]) -> list[EvalTestResult]:
    """Execute a list of test cases and return results.

    Each test function is called with no arguments. Async tests are
    run via ``asyncio.run()``.

    Args:
        cases: List of ``TestCase`` objects to execute.

    Returns:
        List of ``EvalTestResult`` objects, one per test case.
    """
    results: list[EvalTestResult] = []
    for case in cases:
        result = _run_single(case)
        results.append(result)
    return results


def _run_single(case: TestCase) -> EvalTestResult:
    """Execute a single test case and return the result."""
    try:
        if case.is_async:
            asyncio.run(case.func())
        else:
            case.func()
        return EvalTestResult(name=case.name, status="passed")
    except AssertionError as e:
        return EvalTestResult(name=case.name, status="failed", message=str(e))
    except Exception as e:
        tb = traceback.format_exc()
        return EvalTestResult(name=case.name, status="error", message=f"{e}\n{tb}")


def format_results(results: list[EvalTestResult], *, verbose: bool = False) -> str:
    """Format test results as a human-readable string.

    Failure and error messages are **always** shown so problems are
    immediately visible.  The *verbose* flag controls additional detail
    (e.g. full tracebacks).

    Args:
        results: List of ``EvalTestResult`` objects.
        verbose: If True, include full tracebacks for errors.

    Returns:
        Formatted results string.
    """
    lines: list[str] = []
    lines.append("=" * 52 + " test session starts " + "=" * 52)
    lines.append("")

    for r in results:
        if r.status == "passed":
            lines.append(f"{r.name} \u2713")
        elif r.status in ("failed", "error"):
            lines.append(f"{r.name} \u2717")
            if r.message:
                # Always show at least the first line of the message
                msg_lines = r.message.strip().split("\n")
                if verbose:
                    for msg_line in msg_lines:
                        lines.append(f"  {msg_line}")
                else:
                    lines.append(f"  {msg_lines[0]}")

    lines.append("")
    n_passed = sum(1 for r in results if r.status == "passed")
    n_failed = sum(1 for r in results if r.status == "failed")
    n_error = sum(1 for r in results if r.status == "error")

    parts: list[str] = []
    if n_passed:
        parts.append(f"{n_passed} passed")
    if n_failed:
        parts.append(f"{n_failed} failed")
    if n_error:
        parts.append(f"{n_error} errors")

    summary = ", ".join(parts) if parts else "no tests collected"
    lines.append("=" * 47 + f" {summary} " + "=" * 47)
    return "\n".join(lines)
