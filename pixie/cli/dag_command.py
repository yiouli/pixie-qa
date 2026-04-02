"""``pixie dag`` CLI subcommands — validate and check-trace.

Commands::

    pixie dag validate <json_file> [--project-root PATH]
    pixie dag check-trace <json_file>
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from pixie.dag import generate_mermaid, parse_dag, validate_dag
from pixie.dag.trace_check import check_last_trace


def dag_validate(json_file: str, project_root: str | None = None) -> int:
    """Validate a DAG JSON file and generate a Mermaid diagram.

    Returns exit code: 0 on success, 1 on validation failure.
    """
    json_path = Path(json_file)
    nodes, parse_errors = parse_dag(json_path)

    if parse_errors:
        print("PARSE ERRORS:")  # noqa: T201
        for err in parse_errors:
            print(f"  - {err}")  # noqa: T201
        return 1

    root = Path(project_root) if project_root else json_path.parent
    result = validate_dag(nodes, project_root=root)

    if not result.valid:
        print(f"VALIDATION FAILED — {len(result.errors)} error(s):")  # noqa: T201
        for err in result.errors:
            print(f"  - {err}")  # noqa: T201
        if result.warnings:
            for warn in result.warnings:
                print(f"  [warn] {warn}")  # noqa: T201
        return 1

    if result.warnings:
        for warn in result.warnings:
            print(f"  [warn] {warn}")  # noqa: T201

    # Generate Mermaid diagram
    mermaid = generate_mermaid(nodes)
    mermaid_path = json_path.with_suffix(".md")
    mermaid_content = f"# Data Flow DAG\n\n```mermaid\n{mermaid}\n```\n"
    mermaid_path.write_text(mermaid_content, encoding="utf-8")

    print(f"PASSED — DAG is valid ({len(nodes)} nodes).")  # noqa: T201
    print(f"Mermaid diagram written to: {mermaid_path}")  # noqa: T201
    return 0


def dag_check_trace(json_file: str) -> int:
    """Check the last captured trace against a DAG JSON file.

    Returns exit code: 0 if trace matches, 1 otherwise.
    """
    result = asyncio.run(check_last_trace(Path(json_file)))

    if not result.valid:
        print(f"TRACE CHECK FAILED — {len(result.errors)} error(s):")  # noqa: T201
        for err in result.errors:
            print(f"  - {err}")  # noqa: T201
        return 1

    print(  # noqa: T201
        f"TRACE CHECK PASSED — {len(result.matched)} DAG node(s) matched."
    )
    return 0
