"""``pixie analyze`` CLI command.

Generates analysis and recommendations for a test run result by
running an LLM agent (via OpenAI API) on each dataset's results
concurrently, respecting the configured rate limits.

Usage::

    pixie analyze <test_run_id>

The analysis markdown is saved alongside the result JSON at
``<pixie_root>/results/<test_id>/dataset-<index>.md``.
"""

from __future__ import annotations

import asyncio
import json
import os

from pixie.harness.run_result import DatasetResult, load_test_result


def _build_analysis_prompt(ds: DatasetResult) -> str:
    """Build a prompt for analyzing a dataset's evaluation results."""
    lines: list[str] = []
    lines.append(f"Dataset: {ds.dataset}")
    lines.append("")

    passed = sum(1 for e in ds.entries if all(ev.score >= 0.5 for ev in e.evaluations))
    lines.append(f"Overall: {passed}/{len(ds.entries)} entries passed")
    lines.append("")

    for i, entry in enumerate(ds.entries):
        desc = entry.description or str(entry.input)
        all_pass = all(ev.score >= 0.5 for ev in entry.evaluations)
        status = "PASS" if all_pass else "FAIL"
        lines.append(f"Entry {i + 1} ({status}): {desc}")
        lines.append(f"  Input: {json.dumps(entry.input)}")
        lines.append(f"  Output: {json.dumps(entry.output)}")
        if entry.expected_output is not None:
            lines.append(f"  Expected: {json.dumps(entry.expected_output)}")
        for ev in entry.evaluations:
            pass_mark = "PASS" if ev.score >= 0.5 else "FAIL"
            lines.append(
                f"  - {ev.evaluator}: {ev.score:.2f} ({pass_mark}) — {ev.reasoning}"
            )
        lines.append("")

    return "\n".join(lines)


_SYSTEM_PROMPT = """\
You are a QA analysis expert. Given evaluation results from an AI application \
test run, provide:

1. **Summary** — A brief overview of the test results highlighting key patterns.
2. **Failure Analysis** — For each failing scenario, explain what went wrong and \
why the evaluator scored it low.
3. **Recommendations** — Actionable steps to improve the AI application's quality \
based on the failures observed.

Output your analysis as well-structured Markdown. Be concise and actionable. \
Focus on patterns across failures rather than repeating individual scores.\
"""


async def _analyze_dataset(ds: DatasetResult, index: int, result_dir: str) -> str:
    """Run LLM analysis for a single dataset and save the markdown.

    Args:
        ds: The dataset result to analyze.
        index: The dataset index (for the output filename).
        result_dir: Directory to save the analysis markdown.

    Returns:
        The generated analysis markdown content.
    """
    from openai import AsyncOpenAI

    # Rate-limit if configured
    from pixie.eval.rate_limiter import get_rate_limiter

    limiter = get_rate_limiter()
    prompt_text = _build_analysis_prompt(ds)

    if limiter:
        estimated_tokens = limiter.estimate_tokens(prompt_text)
        await limiter.acquire(estimated_tokens)

    client = AsyncOpenAI()
    response = await client.chat.completions.create(
        model=os.environ.get("PIXIE_ANALYZE_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ],
        temperature=0.3,
    )

    content = response.choices[0].message.content or ""

    # Save to disk
    analysis_path = os.path.join(result_dir, f"dataset-{index}.md")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write(content)

    return content


async def _analyze_all(test_id: str) -> None:
    """Analyze all datasets in a test run concurrently."""
    result = load_test_result(test_id)

    from pixie.config import get_config

    config = get_config()
    result_dir = os.path.join(config.root, "results", test_id)

    tasks = [
        _analyze_dataset(ds, i, result_dir) for i, ds in enumerate(result.datasets)
    ]
    await asyncio.gather(*tasks)


def analyze(test_id: str) -> int:
    """Entry point for ``pixie analyze <test_run_id>``.

    Args:
        test_id: The test run identifier to analyze.

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    from pixie.eval.rate_limiter import configure_rate_limits_from_config

    configure_rate_limits_from_config()

    try:
        result = load_test_result(test_id)
    except FileNotFoundError:
        print(f"Error: No test result found for ID {test_id!r}")  # noqa: T201
        return 1

    print(  # noqa: T201
        f"Analyzing {len(result.datasets)} dataset(s) for test run {test_id}..."
    )

    asyncio.run(_analyze_all(test_id))

    from pixie.config import get_config

    config = get_config()
    result_dir = os.path.join(config.root, "results", test_id)
    print(f"Analysis saved to {result_dir}")  # noqa: T201
    return 0
