"""Sample eval test for manual verification of pixie test + scorecard.

Run with:
    PIXIE_ROOT=/tmp/pixie_manual uv run pixie test tests/manual/test_sample.py

Then open the generated HTML scorecard in your browser to inspect the report.
"""

import sys
from pathlib import Path

from pixie import ScoreThreshold, assert_dataset_pass

# Make mock_evaluators importable from this directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mock_evaluators import SimpleFactualityEval, StrictKeywordEval  # noqa: E402

_DATASET_DIR = str(Path(__file__).resolve().parent / "datasets")


async def _noop_runnable(eval_input: object) -> None:
    """No-op — dataset items already carry eval_output."""


async def test_factuality() -> None:
    """All answers should be factually close to expected output.

    Lenient: 50% score threshold, 80% of items must pass.
    Expected: PASS (most items have high string similarity).
    """
    await assert_dataset_pass(
        runnable=_noop_runnable,
        dataset_name="sample-qa",
        evaluators=[SimpleFactualityEval()],
        dataset_dir=_DATASET_DIR,
        pass_criteria=ScoreThreshold(threshold=0.5, pct=0.8),
    )


async def test_keyword_coverage() -> None:
    """All expected keywords should appear in the output.

    Strict: 90% score threshold on all items.
    Expected: FAIL (some items use different phrasing).
    """
    await assert_dataset_pass(
        runnable=_noop_runnable,
        dataset_name="sample-qa",
        evaluators=[StrictKeywordEval()],
        dataset_dir=_DATASET_DIR,
        pass_criteria=ScoreThreshold(threshold=0.9, pct=1.0),
    )


async def test_combined_evaluators() -> None:
    """Both evaluators must pass on every item (strict).

    Expected: FAIL (keyword evaluator is strict enough to fail some items).
    """
    await assert_dataset_pass(
        runnable=_noop_runnable,
        dataset_name="sample-qa",
        evaluators=[SimpleFactualityEval(), StrictKeywordEval()],
        dataset_dir=_DATASET_DIR,
        pass_criteria=ScoreThreshold(threshold=0.7, pct=1.0),
    )
