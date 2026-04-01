"""Data-flow DAG validation and trace checking.

Provides two capabilities:

1. **DAG validation** — validates a JSON file describing the application's
   data-flow DAG (nodes with parent pointers, code pointers, and metadata),
   checks that the DAG is structurally valid and that code pointers refer to
   existing files.  Generates a Mermaid diagram on success.

2. **Trace checking** — validates that the most recent captured trace tree
   matches the expected structure from the DAG JSON, ensuring every DAG node
   with type ``"llm_call"`` or ``"observation"`` has a corresponding span.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Valid node types in the DAG
VALID_NODE_TYPES = frozenset(
    {
        "entry_point",
        "llm_call",
        "data_dependency",
        "intermediate_state",
        "side_effect",
        "observation",
    }
)


@dataclass
class DagNode:
    """A single node in the data-flow DAG."""

    id: str
    name: str
    type: str
    code_pointer: str  # e.g. "src/agents/llm/openai_llm.py:run_ai_response"
    description: str
    parent_id: str | None = None
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
        required = ("id", "name", "type", "code_pointer", "description")
        missing = [f for f in required if f not in item]
        if missing:
            errors.append(
                f"Node at index {i}: missing required fields: {', '.join(missing)}"
            )
            continue

        node = DagNode(
            id=str(item["id"]),
            name=str(item["name"]),
            type=str(item["type"]),
            code_pointer=str(item["code_pointer"]),
            description=str(item["description"]),
            parent_id=(
                str(item["parent_id"]) if item.get("parent_id") is not None else None
            ),
            metadata=item.get("metadata", {}),
        )
        nodes.append(node)

    return nodes, errors


def validate_dag(
    nodes: list[DagNode],
    project_root: Path | None = None,
) -> ValidationResult:
    """Validate the structural integrity of a DAG and its code pointers.

    Checks:
    1. Every node has a valid type.
    2. Every parent_id references an existing node.
    3. Exactly one root node (parent_id is None).
    4. No cycles in the parent chain.
    5. Code pointers reference existing files (if project_root is given).
    """
    result = ValidationResult(valid=True)
    node_ids = {n.id for n in nodes}

    if not nodes:
        result.valid = False
        result.errors.append("DAG is empty — at least one node is required.")
        return result

    # Check for duplicate IDs
    seen_ids: set[str] = set()
    for node in nodes:
        if node.id in seen_ids:
            result.valid = False
            result.errors.append(f"Duplicate node ID: '{node.id}'")
        seen_ids.add(node.id)

    # Check types
    for node in nodes:
        if node.type not in VALID_NODE_TYPES:
            result.valid = False
            result.errors.append(
                f"Node '{node.id}': invalid type '{node.type}'. "
                f"Valid types: {', '.join(sorted(VALID_NODE_TYPES))}"
            )

    # Check parent references
    roots: list[DagNode] = []
    for node in nodes:
        if node.parent_id is None:
            roots.append(node)
        elif node.parent_id not in node_ids:
            result.valid = False
            result.errors.append(
                f"Node '{node.id}': parent_id '{node.parent_id}' does not reference any node."
            )

    if len(roots) == 0:
        result.valid = False
        result.errors.append("No root node found (no node with parent_id=null).")
    elif len(roots) > 1:
        root_ids = [r.id for r in roots]
        result.valid = False
        result.errors.append(
            f"Multiple root nodes found: {', '.join(root_ids)}. "
            "Expected exactly one root."
        )

    # Check for cycles
    for node in nodes:
        visited: set[str] = set()
        current: str | None = node.id
        id_map = {n.id: n for n in nodes}
        while current is not None:
            if current in visited:
                result.valid = False
                result.errors.append(f"Cycle detected involving node '{node.id}'.")
                break
            visited.add(current)
            parent = id_map.get(current)
            current = parent.parent_id if parent else None

    # Check code pointers (file existence)
    if project_root is not None:
        for node in nodes:
            file_part = node.code_pointer.split(":")[0]
            file_path = project_root / file_part
            if not file_path.is_file():
                result.valid = False
                result.errors.append(
                    f"Node '{node.id}': code_pointer file not found: "
                    f"{file_part} (resolved to {file_path})"
                )

    return result


def generate_mermaid(nodes: list[DagNode]) -> str:
    """Generate a Mermaid flowchart from the DAG nodes."""
    lines: list[str] = ["graph TD"]

    # Define nodes with labels
    for node in nodes:
        # Escape special Mermaid characters in labels
        label = node.name.replace('"', "'")
        type_badge = node.type.upper().replace("_", " ")
        shape_open, shape_close = _mermaid_shape(node.type)
        lines.append(
            f'    {node.id}{shape_open}"{label}<br/><i>{type_badge}</i>"{shape_close}'
        )

    # Define edges
    for node in nodes:
        if node.parent_id is not None:
            lines.append(f"    {node.parent_id} --> {node.id}")

    return "\n".join(lines)


def _mermaid_shape(node_type: str) -> tuple[str, str]:
    """Return Mermaid shape delimiters based on node type."""
    shapes: dict[str, tuple[str, str]] = {
        "entry_point": ("([", "])"),
        "llm_call": ("[[", "]]"),
        "data_dependency": ("[(", ")]"),
        "intermediate_state": ("[", "]"),
        "side_effect": ("{{", "}}"),
        "observation": ("(", ")"),
    }
    return shapes.get(node_type, ("[", "]"))
