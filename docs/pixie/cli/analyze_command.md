Module pixie.cli.analyze_command
================================
``pixie analyze`` CLI command.

Generates analysis and recommendations for a test run result by
running an LLM agent (via OpenAI API) on each dataset's results
concurrently, respecting the configured rate limits.

Usage::

    pixie analyze <test_run_id>

The analysis markdown is saved alongside the result JSON at
``<pixie_root>/results/<test_id>/dataset-<index>.md``.

Functions
---------

`analyze(test_id: str) ‑> int`
:   Entry point for ``pixie analyze <test_run_id>``.
    
    Args:
        test_id: The test run identifier to analyze.
    
    Returns:
        Exit code: 0 on success, 1 on error.