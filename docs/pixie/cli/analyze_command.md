Module pixie.cli.analyze_command
================================
``pixie analyze`` CLI command.

Generates deterministic analysis of test run results: per-evaluator
statistics, failure clusters, trace summaries, and cross-dataset patterns.
No LLM calls, no API keys — all computation is from the test result data.

Usage::

    pixie analyze <test_run_id>

Output is saved alongside the result JSON at
``<pixie_root>/results/<test_id>/dataset-<index>.md`` and
``<pixie_root>/results/<test_id>/summary.md``.

Functions
---------

`def analyze(test_id: str) ‑> int`
:   Entry point for ``pixie analyze <test_run_id>``.
    
    Generates deterministic analysis markdown for each dataset and a
    cross-dataset summary.  No LLM calls, no API keys required.
    
    Args:
        test_id: The test run identifier to analyze.
    
    Returns:
        Exit code: 0 on success, 1 on error.