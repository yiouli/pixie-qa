"""End-to-end tests for ``pixie test`` with realistic eval fixtures.

This module contains two complementary test classes:

1. **TestPixieTestRealisticE2E** — the primary e2e test. Runs ``pixie test``
   on a realistic test file (``e2e_fixtures/test_customer_faq.py``) that
   uses ``assert_dataset_pass`` with a 5-item customer-FAQ golden dataset
   and 4 different evaluator/criteria combinations. Mock evaluators
   (deterministic, no LLM calls) produce realistic scores and reasoning.

2. **TestPixieTestEdgeCases** — parametrised edge-case tests loaded from
   ``e2e_cases.json`` covering empty dirs, filters, verbose mode, etc.

After running ``uv run pytest tests/pixie/cli/test_e2e_pixie_test.py -v``,
the coding agent should also manually run the realistic fixture and inspect
the console output + HTML scorecard for correctness. See
``.github/copilot-instructions.md`` section 4a for the full protocol.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pixie.cli.test_command import main as _pixie_test_main

# ── Paths ────────────────────────────────────────────────────────────────

_FIXTURES_DIR = Path(__file__).parent / "e2e_fixtures"
_TEST_FILE = _FIXTURES_DIR / "test_customer_faq.py"
_E2E_CASES_PATH = Path(__file__).parent / "e2e_cases.json"


# ── Helpers ──────────────────────────────────────────────────────────────


def _find_scorecard_html(scorecard_dir: Path) -> str | None:
    """Return the content of the first HTML file in the scorecard dir."""
    if not scorecard_dir.exists():
        return None
    html_files = sorted(scorecard_dir.glob("*.html"))
    if not html_files:
        return None
    return html_files[0].read_text(encoding="utf-8")


def _load_e2e_cases() -> list[dict[str, Any]]:
    """Load edge-case scenarios from the JSON dataset file."""
    with open(_E2E_CASES_PATH, encoding="utf-8") as f:
        cases: list[dict[str, Any]] = json.load(f)
    return cases


_E2E_CASES = _load_e2e_cases()
_CASE_IDS = [c["id"] for c in _E2E_CASES]


# ======================================================================
# 1. Realistic e2e: dataset + evaluators + scoring strategies
# ======================================================================


class TestPixieTestRealisticE2E:
    """Realistic end-to-end test for ``pixie test``.

    Runs ``pixie test`` on ``e2e_fixtures/test_customer_faq.py`` which
    defines 4 async test functions against a 5-item customer-FAQ dataset:

    - ``test_faq_factuality`` — MockFactuality, threshold=0.6, pct=0.8
      → expected PASS (most items score high on string similarity)
    - ``test_faq_multi_evaluator`` — MockFactuality + MockClosedQA,
      threshold=0.5, pct=1.0  → expected FAIL (strict: all items must
      pass both evaluators, and some items have low keyword overlap)
    - ``test_faq_no_hallucinations`` — MockHallucination, threshold=0.5,
      pct=1.0  → expected PASS (mock always returns 0.95)
    - ``test_faq_tone_check`` — MockFailingEval, threshold=0.5, pct=1.0
      → expected FAIL (mock always returns 0.2)
    """

    def test_exit_code_is_1(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Exit code is 1 when any test function fails."""
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path / "pixie_qa"))
        exit_code = _pixie_test_main([str(_TEST_FILE)])
        assert exit_code == 1

    def test_console_reports_2_passed_2_failed(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Console summary shows exactly 2 passed and 2 failed."""
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path / "pixie_qa"))
        _pixie_test_main([str(_TEST_FILE)])
        out = capsys.readouterr().out
        assert "2 passed" in out
        assert "2 failed" in out

    def test_console_lists_all_test_functions(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Console mentions all 4 test function names."""
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path / "pixie_qa"))
        _pixie_test_main([str(_TEST_FILE)])
        out = capsys.readouterr().out
        for name in [
            "test_faq_factuality",
            "test_faq_multi_evaluator",
            "test_faq_no_hallucinations",
            "test_faq_tone_check",
        ]:
            assert name in out, f"Expected '{name}' in console output"

    def test_passing_tests_get_checkmark_failing_get_cross(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Passing tests show ✓ and failing tests show ✗."""
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path / "pixie_qa"))
        _pixie_test_main([str(_TEST_FILE)])
        out = capsys.readouterr().out
        assert "\u2713" in out  # ✓
        assert "\u2717" in out  # ✗

    def test_scorecard_html_is_generated(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """An HTML scorecard file is created."""
        pixie_root = tmp_path / "pixie_qa"
        monkeypatch.setenv("PIXIE_ROOT", str(pixie_root))
        _pixie_test_main([str(_TEST_FILE)])
        html = _find_scorecard_html(pixie_root / "scorecards")
        assert html is not None, "No scorecard HTML was generated"

    def test_scorecard_contains_evaluator_names(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Scorecard HTML includes all mock evaluator names."""
        pixie_root = tmp_path / "pixie_qa"
        monkeypatch.setenv("PIXIE_ROOT", str(pixie_root))
        _pixie_test_main([str(_TEST_FILE)])
        html = _find_scorecard_html(pixie_root / "scorecards")
        assert html is not None
        for name in [
            "MockFactuality",
            "MockClosedQA",
            "MockHallucination",
            "MockStrictTone",
        ]:
            assert name in html, f"Expected '{name}' in scorecard"

    def test_scorecard_shows_pass_and_fail_badges(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Scorecard HTML shows both PASS and FAIL badges."""
        pixie_root = tmp_path / "pixie_qa"
        monkeypatch.setenv("PIXIE_ROOT", str(pixie_root))
        _pixie_test_main([str(_TEST_FILE)])
        html = _find_scorecard_html(pixie_root / "scorecards")
        assert html is not None
        assert "PASS" in html
        assert "FAIL" in html

    def test_scorecard_has_per_input_scores(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Scorecard HTML includes per-input score cells."""
        pixie_root = tmp_path / "pixie_qa"
        monkeypatch.setenv("PIXIE_ROOT", str(pixie_root))
        _pixie_test_main([str(_TEST_FILE)])
        html = _find_scorecard_html(pixie_root / "scorecards")
        assert html is not None
        assert "score-pass" in html or "score-fail" in html

    def test_scorecard_shows_summary_counts(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Scorecard HTML shows 2/4 tests passed."""
        pixie_root = tmp_path / "pixie_qa"
        monkeypatch.setenv("PIXIE_ROOT", str(pixie_root))
        _pixie_test_main([str(_TEST_FILE)])
        html = _find_scorecard_html(pixie_root / "scorecards")
        assert html is not None
        assert "2/4 tests passed" in html

    def test_scorecard_has_scoring_strategy(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Scorecard HTML includes human-readable scoring strategy."""
        pixie_root = tmp_path / "pixie_qa"
        monkeypatch.setenv("PIXIE_ROOT", str(pixie_root))
        _pixie_test_main([str(_TEST_FILE)])
        html = _find_scorecard_html(pixie_root / "scorecards")
        assert html is not None
        # ScoreThreshold produces descriptions mentioning the threshold
        html_lower = html.lower()
        assert "score must be" in html_lower or "must pass" in html_lower


# ======================================================================
# 2. Edge-case tests (parametrised from e2e_cases.json)
# ======================================================================


def _scaffold_test_files(tmp_path: Path, test_files: dict[str, str]) -> None:
    """Write test file contents into the temp directory."""
    for filename, content in test_files.items():
        (tmp_path / filename).write_text(content, encoding="utf-8")


def _build_argv(case: dict[str, Any], tmp_path: Path) -> list[str]:
    """Build the argv list for test_command.main()."""
    argv: list[str] = []
    if "argv_use_file" in case:
        argv.append(str(tmp_path / case["argv_use_file"]))
    else:
        argv.append(str(tmp_path))
    argv.extend(case.get("argv", []))
    return argv


@pytest.fixture(params=_E2E_CASES, ids=_CASE_IDS)
def e2e_case(request: pytest.FixtureRequest) -> dict[str, Any]:
    """Yield each edge-case scenario as a parametrised fixture."""
    case: dict[str, Any] = request.param
    return case


class TestPixieTestEdgeCases:
    """Edge-case tests for ``pixie test`` loaded from ``e2e_cases.json``.

    Covers: empty dirs, filter matching, verbose mode, single file
    targeting, error handling.
    """

    def test_exit_code(
        self,
        e2e_case: dict[str, Any],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Exit code matches expectation."""
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path / "pixie_qa"))
        _scaffold_test_files(tmp_path, e2e_case.get("test_files", {}))
        argv = _build_argv(e2e_case, tmp_path)
        exit_code = _pixie_test_main(argv)
        assert exit_code == e2e_case["expected_exit_code"]

    def test_console_contains(
        self,
        e2e_case: dict[str, Any],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Console output includes all expected strings."""
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path / "pixie_qa"))
        _scaffold_test_files(tmp_path, e2e_case.get("test_files", {}))
        _pixie_test_main(_build_argv(e2e_case, tmp_path))
        out = capsys.readouterr().out
        for s in e2e_case.get("console_contains", []):
            assert s in out, f"Expected '{s}' in output"

    def test_console_not_contains(
        self,
        e2e_case: dict[str, Any],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Console output excludes all forbidden strings."""
        monkeypatch.setenv("PIXIE_ROOT", str(tmp_path / "pixie_qa"))
        _scaffold_test_files(tmp_path, e2e_case.get("test_files", {}))
        _pixie_test_main(_build_argv(e2e_case, tmp_path))
        out = capsys.readouterr().out
        for s in e2e_case.get("console_not_contains", []):
            assert s not in out, f"'{s}' should NOT be in output"

    def test_scorecard_html(
        self,
        e2e_case: dict[str, Any],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Scorecard HTML is generated with expected content."""
        pixie_root = tmp_path / "pixie_qa"
        monkeypatch.setenv("PIXIE_ROOT", str(pixie_root))
        _scaffold_test_files(tmp_path, e2e_case.get("test_files", {}))
        _pixie_test_main(_build_argv(e2e_case, tmp_path))
        html = _find_scorecard_html(pixie_root / "scorecards")
        assert html is not None
        for s in e2e_case.get("scorecard_html_contains", []):
            assert s in html, f"Expected '{s}' in scorecard HTML"
