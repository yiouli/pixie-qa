"""Tests for pixie.dag — DAG parsing, validation, and Mermaid generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pixie.dag import (
    VALID_NODE_TYPES,
    DagNode,
    generate_mermaid,
    parse_dag,
    validate_dag,
)


@pytest.fixture()
def valid_dag_json(tmp_path: Path) -> Path:
    """Create a valid DAG JSON file for testing."""
    dag = [
        {
            "id": "root",
            "name": "handle_request",
            "type": "entry_point",
            "code_pointer": "app.py:handle_request",
            "description": "Main request handler",
            "parent_id": None,
        },
        {
            "id": "llm1",
            "name": "generate_response",
            "type": "llm_call",
            "code_pointer": "app.py:generate_response",
            "description": "OpenAI completion call",
            "parent_id": "root",
        },
        {
            "id": "db_read",
            "name": "fetch_context",
            "type": "data_dependency",
            "code_pointer": "app.py:fetch_context",
            "description": "Read from database",
            "parent_id": "root",
        },
        {
            "id": "save_result",
            "name": "save_response",
            "type": "side_effect",
            "code_pointer": "app.py:save_response",
            "description": "Save to database",
            "parent_id": "root",
        },
    ]
    # Create stub files for code pointers
    (tmp_path / "app.py").write_text("# stub")
    json_path = tmp_path / "data_flow.json"
    json_path.write_text(json.dumps(dag))
    return json_path


class TestParseDag:
    """Tests for parse_dag()."""

    def test_parse_valid_dag(self, valid_dag_json: Path) -> None:
        nodes, errors = parse_dag(valid_dag_json)
        assert not errors
        assert len(nodes) == 4
        assert nodes[0].id == "root"
        assert nodes[0].parent_id is None
        assert nodes[1].parent_id == "root"

    def test_parse_missing_file(self, tmp_path: Path) -> None:
        nodes, errors = parse_dag(tmp_path / "nonexistent.json")
        assert len(errors) == 1
        assert "File not found" in errors[0]

    def test_parse_invalid_json(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json")
        nodes, errors = parse_dag(bad)
        assert len(errors) == 1
        assert "Invalid JSON" in errors[0]

    def test_parse_non_array(self, tmp_path: Path) -> None:
        f = tmp_path / "obj.json"
        f.write_text('{"not": "an array"}')
        nodes, errors = parse_dag(f)
        assert len(errors) == 1
        assert "top-level array" in errors[0]

    def test_parse_missing_required_fields(self, tmp_path: Path) -> None:
        f = tmp_path / "partial.json"
        f.write_text(json.dumps([{"id": "x", "name": "y"}]))
        nodes, errors = parse_dag(f)
        assert len(errors) == 1
        assert "missing required fields" in errors[0]

    def test_parse_non_object_item(self, tmp_path: Path) -> None:
        f = tmp_path / "arr.json"
        f.write_text(json.dumps(["not an object"]))
        nodes, errors = parse_dag(f)
        assert len(errors) == 1
        assert "expected object" in errors[0]


class TestValidateDag:
    """Tests for validate_dag()."""

    def test_valid_dag(self, valid_dag_json: Path) -> None:
        nodes, _ = parse_dag(valid_dag_json)
        result = validate_dag(nodes, project_root=valid_dag_json.parent)
        assert result.valid
        assert not result.errors

    def test_empty_dag(self) -> None:
        result = validate_dag([])
        assert not result.valid
        assert "empty" in result.errors[0].lower()

    def test_invalid_type(self) -> None:
        nodes = [
            DagNode(
                id="n1",
                name="test",
                type="bogus_type",
                code_pointer="f.py:func",
                description="test",
            )
        ]
        result = validate_dag(nodes)
        assert not result.valid
        assert any("invalid type" in e for e in result.errors)

    def test_duplicate_ids(self) -> None:
        nodes = [
            DagNode(
                id="dup",
                name="a",
                type="entry_point",
                code_pointer="f.py:a",
                description="test",
            ),
            DagNode(
                id="dup",
                name="b",
                type="llm_call",
                code_pointer="f.py:b",
                description="test",
                parent_id="dup",
            ),
        ]
        result = validate_dag(nodes)
        assert not result.valid
        assert any("Duplicate" in e for e in result.errors)

    def test_orphan_parent_reference(self) -> None:
        nodes = [
            DagNode(
                id="root",
                name="root",
                type="entry_point",
                code_pointer="f.py:r",
                description="test",
            ),
            DagNode(
                id="child",
                name="child",
                type="llm_call",
                code_pointer="f.py:c",
                description="test",
                parent_id="nonexistent",
            ),
        ]
        result = validate_dag(nodes)
        assert not result.valid
        assert any("does not reference any node" in e for e in result.errors)

    def test_multiple_roots(self) -> None:
        nodes = [
            DagNode(
                id="r1",
                name="root1",
                type="entry_point",
                code_pointer="f.py:r1",
                description="test",
            ),
            DagNode(
                id="r2",
                name="root2",
                type="entry_point",
                code_pointer="f.py:r2",
                description="test",
            ),
        ]
        result = validate_dag(nodes)
        assert not result.valid
        assert any("Multiple root" in e for e in result.errors)

    def test_no_root(self) -> None:
        nodes = [
            DagNode(
                id="a",
                name="a",
                type="llm_call",
                code_pointer="f.py:a",
                description="test",
                parent_id="b",
            ),
            DagNode(
                id="b",
                name="b",
                type="llm_call",
                code_pointer="f.py:b",
                description="test",
                parent_id="a",
            ),
        ]
        result = validate_dag(nodes)
        assert not result.valid
        assert any("No root" in e for e in result.errors)

    def test_code_pointer_file_missing(self, tmp_path: Path) -> None:
        nodes = [
            DagNode(
                id="n1",
                name="test",
                type="entry_point",
                code_pointer="missing_file.py:func",
                description="test",
            )
        ]
        result = validate_dag(nodes, project_root=tmp_path)
        assert not result.valid
        assert any("not found" in e for e in result.errors)

    def test_code_pointer_file_exists(self, tmp_path: Path) -> None:
        (tmp_path / "exists.py").write_text("# ok")
        nodes = [
            DagNode(
                id="n1",
                name="test",
                type="entry_point",
                code_pointer="exists.py:func",
                description="test",
            )
        ]
        result = validate_dag(nodes, project_root=tmp_path)
        assert result.valid

    def test_cycle_detection(self) -> None:
        """Cycle: a -> b -> a."""
        nodes = [
            DagNode(
                id="a",
                name="a",
                type="entry_point",
                code_pointer="f.py:a",
                description="test",
                parent_id="b",
            ),
            DagNode(
                id="b",
                name="b",
                type="llm_call",
                code_pointer="f.py:b",
                description="test",
                parent_id="a",
            ),
        ]
        result = validate_dag(nodes)
        assert not result.valid
        assert any("Cycle" in e or "No root" in e for e in result.errors)


class TestGenerateMermaid:
    """Tests for generate_mermaid()."""

    def test_generates_valid_mermaid(self) -> None:
        nodes = [
            DagNode(
                id="root",
                name="handle_request",
                type="entry_point",
                code_pointer="app.py:handle",
                description="entry",
            ),
            DagNode(
                id="llm1",
                name="call_openai",
                type="llm_call",
                code_pointer="app.py:llm",
                description="LLM call",
                parent_id="root",
            ),
        ]
        mermaid = generate_mermaid(nodes)
        assert "graph TD" in mermaid
        assert "root" in mermaid
        assert "llm1" in mermaid
        assert "root --> llm1" in mermaid

    def test_node_shapes_differ_by_type(self) -> None:
        for node_type in VALID_NODE_TYPES:
            nodes = [
                DagNode(
                    id="n",
                    name="test",
                    type=node_type,
                    code_pointer="f.py:f",
                    description="test",
                )
            ]
            mermaid = generate_mermaid(nodes)
            assert "graph TD" in mermaid
