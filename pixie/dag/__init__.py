"""Data-flow DAG parsing, validation, and Mermaid generation.

The DAG schema is intentionally simple:

- ``name`` is the unique lower_snake_case node identifier.
- ``parent`` (or legacy ``parent_id``) links nodes into a tree.
- ``is_llm_call`` marks nodes that represent LLM spans during trace checks.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Lower snake_case node names, e.g. "handle_turn".
DAG_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def is_valid_dag_name(name: str) -> bool:
    """Return whether *name* matches lower_snake_case DAG naming."""
    return DAG_NAME_PATTERN.fullmatch(name) is not None


@dataclass
class DagNode:
    """A single node in the data-flow DAG."""

    name: str
    # Absolute or relative file path with symbol and optional line range.
    # Format: <file_path>:<symbol> or <file_path>:<symbol>:<start_line>:<end_line>
    # Examples:
    #   /home/user/myproject/app.py:MyClass.func
    #   /home/user/myproject/app.py:MyClass.func:51:71
    #   src/agents/llm/openai_llm.py:run_ai_response  (relative, legacy)
    code_pointer: str
    description: str
    parent: str | None = None
    is_llm_call: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of a DAG or trace validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_dag(json_path: Path) -> tuple[list[DagNode], list[str]]:
    """Parse a DAG JSON file into a list of DagNode objects.

    Returns ``(nodes, errors)`` where *errors* is empty on success.
    """
    errors: list[str] = []
    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [], [f"Invalid JSON: {exc}"]
    except FileNotFoundError:
        return [], [f"File not found: {json_path}"]

    if not isinstance(raw, list):
        return [], ["DAG JSON must be a top-level array of node objects."]

    nodes: list[DagNode] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            errors.append(
                f"Node at index {i}: expected object, got {type(item).__name__}"
            )
            continue

        # Required fields
        required = ("name", "code_pointer", "description")
        missing = [f for f in required if f not in item]
        if missing:
            errors.append(
                f"Node at index {i}: missing required fields: {', '.join(missing)}"
            )
            continue

        # Optional metadata must be an object when present.
        metadata_raw = item.get("metadata", {})
        if not isinstance(metadata_raw, dict):
            errors.append(
                f"Node '{item.get('name', f'index {i}')}' metadata must be an object."
            )
            continue

        # ``is_llm_call`` defaults to False when omitted.
        is_llm_call_raw = item.get("is_llm_call", False)
        if not isinstance(is_llm_call_raw, bool):
            errors.append(f"Node '{item['name']}': is_llm_call must be true or false.")
            continue

        # Backward-compatible parent parsing: prefer ``parent`` but accept
        # legacy ``parent_id`` for existing DAG files.
        parent_raw = item.get("parent")
        legacy_parent_raw = item.get("parent_id")
        if (
            parent_raw is not None
            and legacy_parent_raw is not None
            and str(parent_raw) != str(legacy_parent_raw)
        ):
            errors.append(f"Node '{item['name']}': parent and parent_id disagree.")
            continue
        parent_name_raw = parent_raw if "parent" in item else legacy_parent_raw

        node = DagNode(
            name=str(item["name"]),
            code_pointer=str(item["code_pointer"]),
            description=str(item["description"]),
            parent=(str(parent_name_raw) if parent_name_raw is not None else None),
            is_llm_call=is_llm_call_raw,
            metadata=metadata_raw,
        )
        nodes.append(node)

    return nodes, errors


def validate_dag(
    nodes: list[DagNode],
    project_root: Path | None = None,
) -> ValidationResult:
    """Validate the structural integrity of a DAG and its code pointers.

    Checks:
    1. Node names are unique.
    2. Node names use lower_snake_case.
    3. Every parent reference points to an existing node name.
    4. Exactly one root node (parent is None).
    5. No cycles in the parent chain.
    6. Code pointers reference existing files (if project_root is given).
    """
    result = ValidationResult(valid=True)
    node_names = {n.name for n in nodes}

    if not nodes:
        result.valid = False
        result.errors.append("DAG is empty — at least one node is required.")
        return result

    # Check for duplicate node names
    seen_names: set[str] = set()
    for node in nodes:
        if node.name in seen_names:
            result.valid = False
            result.errors.append(f"Duplicate node name: '{node.name}'")
        seen_names.add(node.name)

    # Enforce lower_snake_case names for both node and parent references.
    for node in nodes:
        if not is_valid_dag_name(node.name):
            result.valid = False
            result.errors.append(
                f"Node '{node.name}': name must be lower_snake_case "
                "(e.g., 'handle_turn')."
            )
        if node.parent is not None and not is_valid_dag_name(node.parent):
            result.valid = False
            result.errors.append(
                f"Node '{node.name}': parent '{node.parent}' must be "
                "lower_snake_case."
            )

    # Check parent references
    roots: list[DagNode] = []
    for node in nodes:
        if node.parent is None:
            roots.append(node)
        elif node.parent not in node_names:
            result.valid = False
            result.errors.append(
                f"Node '{node.name}': parent '{node.parent}' does not reference any node."
            )

    if len(roots) == 0:
        result.valid = False
        result.errors.append("No root node found (no node with parent=null).")
    elif len(roots) > 1:
        root_names = [r.name for r in roots]
        result.valid = False
        result.errors.append(
            f"Multiple root nodes found: {', '.join(root_names)}. "
            "Expected exactly one root."
        )

    # Check for cycles
    name_map = {n.name: n for n in nodes}
    for node in nodes:
        visited: set[str] = set()
        current: str | None = node.name
        while current is not None:
            if current in visited:
                result.valid = False
                result.errors.append(f"Cycle detected involving node '{node.name}'.")
                break
            visited.add(current)
            parent = name_map.get(current)
            current = parent.parent if parent else None

    # Check code pointers (file existence, symbol, line ranges)
    for node in nodes:
        file_str, symbol, start_line, end_line, parse_err = _parse_code_pointer(
            node.code_pointer
        )
        if parse_err is not None:
            result.valid = False
            result.errors.append(
                f"Node '{node.name}': invalid code_pointer: {parse_err}"
            )
            continue

        # Resolve file path (absolute or relative)
        file_path_obj = Path(file_str)
        if not file_path_obj.is_absolute():
            if project_root is None:
                # Can't resolve relative paths without project_root
                continue
            file_path_obj = project_root / file_str

        if not file_path_obj.is_file():
            result.valid = False
            result.errors.append(
                f"Node '{node.name}': code_pointer file not found: {file_path_obj}"
            )
            continue

        # Check symbol exists in the file
        sym_err = _check_symbol_in_file(file_path_obj, symbol)
        if sym_err is not None:
            result.valid = False
            result.errors.append(f"Node '{node.name}': {sym_err}")

        # Check line number range validity
        if start_line is not None and end_line is not None:
            line_err = _check_line_range(file_path_obj, start_line, end_line)
            if line_err is not None:
                result.valid = False
                result.errors.append(f"Node '{node.name}': {line_err}")

    return result


def _parse_code_pointer(
    code_pointer: str,
) -> tuple[str, str, int | None, int | None, str | None]:
    """Parse code_pointer into (file_path, symbol, start_line, end_line, error).

    Format: ``<file_path>:<symbol>`` or ``<file_path>:<symbol>:<start>:<end>``.
    Absolute paths start with ``/``.

    Returns a 5-tuple. If *error* is not None the other fields are empty strings / None.
    """
    # Find the split point: first ':' after '.py'
    py_idx = code_pointer.find(".py:")
    if py_idx == -1:
        return (
            "",
            "",
            None,
            None,
            (f"code_pointer must contain '<file>.py:<symbol>', got '{code_pointer}'"),
        )

    file_str = code_pointer[: py_idx + 3]  # includes '.py'
    rest = code_pointer[py_idx + 4 :]  # after '.py:'

    if not rest:
        return (
            "",
            "",
            None,
            None,
            (f"code_pointer missing symbol after file path in '{code_pointer}'"),
        )

    parts = rest.split(":")
    symbol = parts[0]
    start_line: int | None = None
    end_line: int | None = None

    if len(parts) == 1:
        pass  # just symbol
    elif len(parts) == 3:
        try:
            start_line = int(parts[1])
            end_line = int(parts[2])
        except ValueError:
            return (
                "",
                "",
                None,
                None,
                (f"Invalid line numbers in code_pointer '{code_pointer}'"),
            )
    else:
        return (
            "",
            "",
            None,
            None,
            (
                f"code_pointer must be '<file>:<symbol>' or "
                f"'<file>:<symbol>:<start>:<end>', got '{code_pointer}'"
            ),
        )

    return file_str, symbol, start_line, end_line, None


def _check_symbol_in_file(file_path: Path, symbol: str) -> str | None:
    """Check if *symbol* exists in *file_path*. Returns error message or None."""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError) as exc:
        return f"Cannot parse {file_path}: {exc}"

    parts = symbol.split(".")
    if len(parts) == 1:
        # Simple function/class name
        func_or_class = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        for node in ast.walk(tree):
            if isinstance(node, func_or_class) and node.name == parts[0]:
                return None
        return f"Symbol '{symbol}' not found in {file_path}"
    elif len(parts) == 2:
        # Class.method
        class_name, method_name = parts
        func_types = (ast.FunctionDef, ast.AsyncFunctionDef)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, func_types) and item.name == method_name:
                        return None
                return (
                    f"Method '{method_name}' not found in class "
                    f"'{class_name}' in {file_path}"
                )
        return f"Class '{class_name}' not found in {file_path}"
    else:
        return (
            f"Invalid symbol format '{symbol}' — expected 'func_name' or 'Class.method'"
        )


def _check_line_range(file_path: Path, start: int, end: int) -> str | None:
    """Validate that *start*..*end* is a valid line range in *file_path*."""
    if start > end:
        return (
            f"Invalid line range {start}:{end} in {file_path} — " "start must be <= end"
        )
    line_count = len(file_path.read_text(encoding="utf-8").splitlines())
    if start < 1:
        return f"Invalid start line {start} in {file_path} — must be >= 1"
    if end > line_count:
        return (
            f"Line range {start}:{end} exceeds file length ({line_count} lines) "
            f"in {file_path}"
        )
    return None


def generate_mermaid(nodes: list[DagNode]) -> str:
    """Generate a Mermaid flowchart from the DAG nodes."""
    lines: list[str] = ["graph TD"]
    mermaid_ids = {node.name: f"n{i}" for i, node in enumerate(nodes)}

    # Define nodes with labels
    for node in nodes:
        # Escape special Mermaid characters in labels
        label = node.name.replace('"', "'")
        if node.is_llm_call:
            label = f"{label}<br/><i>LLM</i>"
        shape_open, shape_close = _mermaid_shape(node)
        lines.append(f'    {mermaid_ids[node.name]}{shape_open}"{label}"{shape_close}')

    # Define edges
    for node in nodes:
        if node.parent is not None:
            lines.append(f"    {mermaid_ids[node.parent]} --> {mermaid_ids[node.name]}")

    return "\n".join(lines)


def _mermaid_shape(node: DagNode) -> tuple[str, str]:
    """Return Mermaid shape delimiters based on root/LLM flags."""
    if node.parent is None:
        return "([", "])"
    if node.is_llm_call:
        return "[[", "]]"
    return "[", "]"
