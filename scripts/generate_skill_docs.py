#!/usr/bin/env python3
"""Generate skill reference docs from pixie source code docstrings using pdoc.

Produces three Markdown files from module and function docstrings — the script
contains **no documentation content itself**.  All content comes from the source
code docstrings, extracted via ``pdoc.doc.Module``.

Output files:

- ``evaluators.md``  — from ``pixie.evals.scorers`` + ``pixie.evals.llm_evaluator``
- ``wrap-api.md``    — from ``pixie.instrumentation.wrap`` + related modules
- ``testing-api.md`` — from ``pixie.evals`` (module docstring + key members)

Usage::

    uv run python scripts/generate_skill_docs.py                # writes to docs/skill-references/
    uv run python scripts/generate_skill_docs.py -o /tmp/refs   # custom output directory
"""

from __future__ import annotations

import argparse
import inspect
from pathlib import Path

from pdoc.doc import Module


def _sig(obj: object) -> str:
    """Return the call signature, or empty string on failure."""
    try:
        return str(inspect.signature(obj))  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return ""


def _render_module_doc(mod: Module) -> str:
    """Render a module's docstring as a markdown section."""
    return mod.docstring


def _render_member(name: str, obj: object, prefix: str = "") -> str:
    """Render a single function/class as a markdown section with signature + docstring."""
    lines: list[str] = []
    sig = _sig(obj)
    display = f"{prefix}{name}" if prefix else name
    lines.append(f"### `{display}`")
    lines.append("")
    if sig:
        lines.append("```python")
        lines.append(f"{display}{sig}")
        lines.append("```")
        lines.append("")
    doc = inspect.getdoc(obj) or ""
    if doc:
        lines.append(doc)
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# evaluators.md — from pixie.evals.scorers + pixie.evals.llm_evaluator
# ---------------------------------------------------------------------------


def _generate_evaluators_md() -> str:
    """Generate evaluators.md from scorers and llm_evaluator module docstrings."""
    scorers_mod = Module.from_name("pixie.evals.scorers")
    llm_mod = Module.from_name("pixie.evals.llm_evaluator")

    lines: list[str] = []
    lines.append("# Built-in Evaluators")
    lines.append("")
    lines.append("> Auto-generated from pixie source code docstrings.")
    lines.append(
        "> Do not edit by hand — run `uv run python scripts/generate_skill_docs.py`."
    )
    lines.append("")

    # Module-level docstring (includes the selection guide)
    lines.append(_render_module_doc(scorers_mod))
    lines.append("")
    lines.append("---")
    lines.append("")

    # Each evaluator function
    lines.append("## Evaluator Reference")
    lines.append("")
    for member in scorers_mod.own_members:
        if member.kind == "function" and not member.name.startswith("_"):
            obj = member.obj
            lines.append(_render_member(member.name, obj))

    # create_llm_evaluator from llm_evaluator module
    lines.append("---")
    lines.append("")
    lines.append("## Custom Evaluators: `create_llm_evaluator`")
    lines.append("")
    lines.append(_render_module_doc(llm_mod))
    lines.append("")
    for member in llm_mod.own_members:
        if member.name == "create_llm_evaluator":
            lines.append(_render_member(member.name, member.obj))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# wrap-api.md — from pixie.instrumentation.wrap + related modules
# ---------------------------------------------------------------------------

# Error types to extract from the wrap module
_WRAP_ERROR_TYPES = ["WrapRegistryMissError", "WrapTypeMismatchError"]

# Trace file utility types and functions
_WRAP_TRACE_UTILS = ["WrapLogEntry", "load_wrap_log_entries", "filter_by_purpose"]


def _generate_wrap_api_md() -> str:
    """Generate wrap-api.md from wrap, wrap_log, and related module docstrings."""
    import pixie

    wrap_mod = Module.from_name("pixie.instrumentation.wrap")
    wrap_log_mod = Module.from_name("pixie.instrumentation.wrap_log")

    lines: list[str] = []
    lines.append("# Wrap API Reference")
    lines.append("")
    lines.append("> Auto-generated from pixie source code docstrings.")
    lines.append(
        "> Do not edit by hand — run `uv run python scripts/generate_skill_docs.py`."
    )
    lines.append("")

    # Module-level docstring (includes mode descriptions)
    lines.append(_render_module_doc(wrap_mod))
    lines.append("")
    lines.append("---")
    lines.append("")

    # Environment variables and CLI commands from config
    lines.append("## Environment Variables")
    lines.append("")
    lines.append("| Variable | Default | Description |")
    lines.append("| --- | --- | --- |")
    lines.append(
        "| `PIXIE_TRACING` | unset | Set to `1` to enable tracing mode for "
        "`wrap()`.  When unset, `wrap()` is a no-op at runtime (eval mode is "
        "controlled by the test runner via the wrap registry, independent of "
        "this flag). |"
    )
    lines.append(
        "| `PIXIE_TRACE_OUTPUT` | unset | Path to a JSONL file where `wrap()` "
        "events and LLM spans are written during a tracing run.  Requires "
        "`PIXIE_TRACING=1`. |"
    )
    lines.append("")

    lines.append("## CLI Commands")
    lines.append("")
    lines.append("| Command | Description |")
    lines.append("| --- | --- |")
    lines.append(
        "| `pixie trace filter <file.jsonl> --purpose entry,input` | Print only "
        "wrap events matching the given purposes.  Outputs one JSON line per "
        "matching event. |"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    # wrap() function
    lines.append("## Functions")
    lines.append("")
    wrap_member = wrap_mod.get("wrap")
    if wrap_member is not None:
        lines.append(_render_member("wrap", wrap_member.obj, prefix="pixie."))

    # enable_storage
    if hasattr(pixie, "enable_storage"):
        lines.append(
            _render_member("enable_storage", pixie.enable_storage, prefix="pixie.")
        )

    lines.append("---")
    lines.append("")

    # Error types
    lines.append("## Error Types")
    lines.append("")
    for name in _WRAP_ERROR_TYPES:
        obj = getattr(pixie, name, None)
        if obj is not None:
            lines.append(_render_member(name, obj))

    lines.append("---")
    lines.append("")

    # Trace file utilities
    lines.append("## Trace File Utilities")
    lines.append("")
    lines.append(_render_module_doc(wrap_log_mod))
    lines.append("")
    for name in _WRAP_TRACE_UTILS:
        obj = getattr(pixie, name, None)
        if obj is not None:
            lines.append(_render_member(name, obj, prefix="pixie."))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# testing-api.md — from pixie.evals
# ---------------------------------------------------------------------------

# Key members to extract from pixie for testing API
_TESTING_TYPES = ["Evaluable", "Evaluation", "ScoreThreshold"]
_TESTING_FUNCTIONS = ["run_and_evaluate", "assert_pass", "assert_dataset_pass"]
_TRACE_HELPERS = ["last_llm_call", "root", "capture_traces"]


def _generate_testing_api_md() -> str:
    """Generate testing-api.md from the evals package docstrings."""
    import pixie

    mod = Module.from_name("pixie.evals")

    lines: list[str] = []
    lines.append("# Testing API Reference")
    lines.append("")
    lines.append("> Auto-generated from pixie source code docstrings.")
    lines.append(
        "> Do not edit by hand — run `uv run python scripts/generate_skill_docs.py`."
    )
    lines.append("")

    # Module-level docstring (includes dataset JSON format, CLI commands, etc.)
    lines.append(_render_module_doc(mod))
    lines.append("")
    lines.append("---")
    lines.append("")

    # Types
    lines.append("## Types")
    lines.append("")
    for name in _TESTING_TYPES:
        obj = getattr(pixie, name, None)
        if obj is not None:
            lines.append(_render_member(name, obj))

    # Eval functions
    lines.append("## Eval Functions")
    lines.append("")
    for name in _TESTING_FUNCTIONS:
        obj = getattr(pixie, name, None)
        if obj is not None:
            lines.append(_render_member(name, obj, prefix="pixie."))

    # Trace helpers
    lines.append("## Trace Helpers")
    lines.append("")
    for name in _TRACE_HELPERS:
        obj = getattr(pixie, name, None)
        if obj is not None:
            lines.append(_render_member(name, obj, prefix="pixie."))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Generate all skill reference docs."""
    parser = argparse.ArgumentParser(
        description="Generate skill reference docs from pixie source code.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output directory (default: docs/skill-references/)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else Path("docs/skill-references")
    output_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "evaluators.md": _generate_evaluators_md,
        "wrap-api.md": _generate_wrap_api_md,
        "testing-api.md": _generate_testing_api_md,
    }

    for filename, generator in files.items():
        content = generator()
        path = output_dir / filename
        path.write_text(content, encoding="utf-8")
        print(f"  wrote {path}")  # noqa: T201

    print(f"\n  Generated {len(files)} reference docs in {output_dir}/")  # noqa: T201


if __name__ == "__main__":
    main()
