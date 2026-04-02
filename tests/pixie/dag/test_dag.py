"""Tests for pixie.dag — DAG parsing, validation, and Mermaid generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pixie.dag import (
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
            "name": "handle_request",
            "code_pointer": "app.py:handle_request",
            "description": "Main request handler",
            "parent": None,
        },
        {
            "name": "generate_response",
            "code_pointer": "app.py:generate_response",
            "description": "OpenAI completion call",
            "parent": "handle_request",
            "is_llm_call": True,
        },
        {
            "name": "fetch_context",
            "code_pointer": "app.py:fetch_context",
            "description": "Read from database",
            "parent": "handle_request",
        },
        {
            "name": "save_response",
            "code_pointer": "app.py:save_response",
            "description": "Save to database",
            "parent": "handle_request",
        },
    ]
    # Create stub files for code pointers with actual function definitions
    (tmp_path / "app.py").write_text(
        "def handle_request(): pass\n"
        "def generate_response(): pass\n"
        "def fetch_context(): pass\n"
        "def save_response(): pass\n"
    )
    json_path = tmp_path / "data_flow.json"
    json_path.write_text(json.dumps(dag))
    return json_path


class TestParseDag:
    """Tests for parse_dag()."""

    def test_parse_valid_dag(self, valid_dag_json: Path) -> None:
        nodes, errors = parse_dag(valid_dag_json)
        assert not errors
        assert len(nodes) == 4
        assert nodes[0].name == "handle_request"
        assert nodes[0].parent is None
        assert nodes[1].parent == "handle_request"
        assert nodes[1].is_llm_call
        assert not nodes[2].is_llm_call

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
        f.write_text(json.dumps([{"name": "y"}]))
        nodes, errors = parse_dag(f)
        assert len(errors) == 1
        assert "missing required fields" in errors[0]

    def test_parse_non_object_item(self, tmp_path: Path) -> None:
        f = tmp_path / "arr.json"
        f.write_text(json.dumps(["not an object"]))
        nodes, errors = parse_dag(f)
        assert len(errors) == 1
        assert "expected object" in errors[0]

    def test_parse_rejects_non_bool_is_llm_call(self, tmp_path: Path) -> None:
        f = tmp_path / "bad_llm_flag.json"
        f.write_text(
            json.dumps(
                [
                    {
                        "name": "foo",
                        "code_pointer": "app.py:foo",
                        "description": "x",
                        "is_llm_call": "yes",
                    }
                ]
            )
        )
        nodes, errors = parse_dag(f)
        assert not nodes
        assert len(errors) == 1
        assert "is_llm_call must be true or false" in errors[0]

    def test_parse_accepts_legacy_parent_id(self, tmp_path: Path) -> None:
        f = tmp_path / "legacy_parent.json"
        f.write_text(
            json.dumps(
                [
                    {
                        "name": "root",
                        "code_pointer": "app.py:root",
                        "description": "root",
                    },
                    {
                        "name": "child_node",
                        "code_pointer": "app.py:child",
                        "description": "child",
                        "parent_id": "root",
                    },
                ]
            )
        )
        nodes, errors = parse_dag(f)
        assert not errors
        assert nodes[1].parent == "root"

    def test_validate_rejects_non_snake_case_name(self) -> None:
        nodes = [
            DagNode(
                name="handle-request",
                code_pointer="f.py:root",
                description="invalid style",
            )
        ]
        result = validate_dag(nodes)
        assert not result.valid
        assert any("lower_snake_case" in e for e in result.errors)


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

    def test_duplicate_names(self) -> None:
        nodes = [
            DagNode(
                name="a",
                code_pointer="f.py:a",
                description="test",
            ),
            DagNode(
                name="a",
                code_pointer="f.py:b",
                description="test",
                parent="a",
                is_llm_call=True,
            ),
        ]
        result = validate_dag(nodes)
        assert not result.valid
        assert any("Duplicate" in e for e in result.errors)

    def test_orphan_parent_reference(self) -> None:
        nodes = [
            DagNode(
                name="root",
                code_pointer="f.py:r",
                description="test",
            ),
            DagNode(
                name="child",
                code_pointer="f.py:c",
                description="test",
                parent="nonexistent",
                is_llm_call=True,
            ),
        ]
        result = validate_dag(nodes)
        assert not result.valid
        assert any("does not reference any node" in e for e in result.errors)

    def test_multiple_roots(self) -> None:
        nodes = [
            DagNode(
                name="root1",
                code_pointer="f.py:r1",
                description="test",
            ),
            DagNode(
                name="root2",
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
                name="a",
                code_pointer="f.py:a",
                description="test",
                parent="b",
                is_llm_call=True,
            ),
            DagNode(
                name="b",
                code_pointer="f.py:b",
                description="test",
                parent="a",
                is_llm_call=True,
            ),
        ]
        result = validate_dag(nodes)
        assert not result.valid
        assert any("No root" in e for e in result.errors)

    def test_code_pointer_file_missing(self, tmp_path: Path) -> None:
        nodes = [
            DagNode(
                name="test",
                code_pointer=f"{tmp_path}/missing_file.py:func",
                description="test",
            )
        ]
        result = validate_dag(nodes)
        assert not result.valid
        assert any("not found" in e for e in result.errors)

    def test_code_pointer_file_exists(self, tmp_path: Path) -> None:
        (tmp_path / "exists.py").write_text("def func(): pass\n")
        nodes = [
            DagNode(
                name="test",
                code_pointer=f"{tmp_path}/exists.py:func",
                description="test",
            )
        ]
        result = validate_dag(nodes)
        assert result.valid

    def test_relative_code_pointer_file_exists(self, tmp_path: Path) -> None:
        """Backward compat: relative paths still work with project_root."""
        (tmp_path / "exists.py").write_text("def func(): pass\n")
        nodes = [
            DagNode(
                name="test",
                code_pointer="exists.py:func",
                description="test",
            )
        ]
        result = validate_dag(nodes, project_root=tmp_path)
        assert result.valid

    def test_relative_code_pointer_file_missing(self, tmp_path: Path) -> None:
        """Backward compat: relative paths still report missing files."""
        nodes = [
            DagNode(
                name="test",
                code_pointer="missing_file.py:func",
                description="test",
            )
        ]
        result = validate_dag(nodes, project_root=tmp_path)
        assert not result.valid
        assert any("not found" in e for e in result.errors)

    def test_cycle_detection(self) -> None:
        """Cycle: a -> b -> a."""
        nodes = [
            DagNode(
                name="a",
                code_pointer="f.py:a",
                description="test",
                parent="b",
            ),
            DagNode(
                name="b",
                code_pointer="f.py:b",
                description="test",
                parent="a",
                is_llm_call=True,
            ),
        ]
        result = validate_dag(nodes)
        assert not result.valid
        assert any("Cycle" in e or "No root" in e for e in result.errors)


class TestCodePointerValidation:
    """Tests for absolute-path code_pointer with symbol and line range validation."""

    def test_absolute_path_symbol_exists(self, tmp_path: Path) -> None:
        (tmp_path / "module.py").write_text("def my_func():\n    pass\n")
        nodes = [
            DagNode(
                name="test",
                code_pointer=f"{tmp_path}/module.py:my_func",
                description="test",
            )
        ]
        result = validate_dag(nodes)
        assert result.valid

    def test_absolute_path_symbol_not_found(self, tmp_path: Path) -> None:
        (tmp_path / "module.py").write_text("def other_func():\n    pass\n")
        nodes = [
            DagNode(
                name="test",
                code_pointer=f"{tmp_path}/module.py:nonexistent",
                description="test",
            )
        ]
        result = validate_dag(nodes)
        assert not result.valid
        assert any("Symbol 'nonexistent' not found" in e for e in result.errors)

    def test_absolute_path_class_method(self, tmp_path: Path) -> None:
        src = "class MyClass:\n" "    def my_method(self):\n" "        pass\n"
        (tmp_path / "module.py").write_text(src)
        nodes = [
            DagNode(
                name="test",
                code_pointer=f"{tmp_path}/module.py:MyClass.my_method",
                description="test",
            )
        ]
        result = validate_dag(nodes)
        assert result.valid

    def test_absolute_path_class_method_not_found(self, tmp_path: Path) -> None:
        src = "class MyClass:\n" "    def existing(self):\n" "        pass\n"
        (tmp_path / "module.py").write_text(src)
        nodes = [
            DagNode(
                name="test",
                code_pointer=f"{tmp_path}/module.py:MyClass.missing",
                description="test",
            )
        ]
        result = validate_dag(nodes)
        assert not result.valid
        assert any(
            "Method 'missing' not found in class 'MyClass'" in e for e in result.errors
        )

    def test_absolute_path_class_not_found(self, tmp_path: Path) -> None:
        (tmp_path / "module.py").write_text("def func():\n    pass\n")
        nodes = [
            DagNode(
                name="test",
                code_pointer=f"{tmp_path}/module.py:NoSuchClass.method",
                description="test",
            )
        ]
        result = validate_dag(nodes)
        assert not result.valid
        assert any("Class 'NoSuchClass' not found" in e for e in result.errors)

    def test_valid_line_range(self, tmp_path: Path) -> None:
        src = "\n".join(f"# line {i}" for i in range(1, 11)) + "\n"
        src += "def my_func():\n    pass\n"
        (tmp_path / "module.py").write_text(src)
        nodes = [
            DagNode(
                name="test",
                code_pointer=f"{tmp_path}/module.py:my_func:5:10",
                description="test",
            )
        ]
        result = validate_dag(nodes)
        assert result.valid

    def test_invalid_line_range_start_gt_end(self, tmp_path: Path) -> None:
        src = "def my_func():\n    pass\n"
        (tmp_path / "module.py").write_text(src)
        nodes = [
            DagNode(
                name="test",
                code_pointer=f"{tmp_path}/module.py:my_func:10:5",
                description="test",
            )
        ]
        result = validate_dag(nodes)
        assert not result.valid
        assert any("start must be <= end" in e for e in result.errors)

    def test_invalid_line_range_out_of_bounds(self, tmp_path: Path) -> None:
        src = "def my_func():\n    pass\n"
        (tmp_path / "module.py").write_text(src)
        nodes = [
            DagNode(
                name="test",
                code_pointer=f"{tmp_path}/module.py:my_func:1:100",
                description="test",
            )
        ]
        result = validate_dag(nodes)
        assert not result.valid
        assert any("exceeds file length" in e for e in result.errors)

    def test_async_function_symbol(self, tmp_path: Path) -> None:
        (tmp_path / "module.py").write_text("async def async_handler():\n    pass\n")
        nodes = [
            DagNode(
                name="test",
                code_pointer=f"{tmp_path}/module.py:async_handler",
                description="test",
            )
        ]
        result = validate_dag(nodes)
        assert result.valid

    def test_relative_path_skipped_without_project_root(self) -> None:
        """Relative paths without project_root skip file resolution."""
        nodes = [
            DagNode(
                name="test",
                code_pointer="some/path.py:func",
                description="test",
            )
        ]
        result = validate_dag(nodes)
        # No project_root, relative path — file check is skipped
        assert result.valid


class TestGenerateMermaid:
    """Tests for generate_mermaid()."""

    def test_generates_valid_mermaid(self) -> None:
        nodes = [
            DagNode(
                name="handle_request",
                code_pointer="app.py:handle",
                description="entry",
            ),
            DagNode(
                name="call_openai",
                code_pointer="app.py:llm",
                description="LLM call",
                parent="handle_request",
                is_llm_call=True,
            ),
        ]
        mermaid = generate_mermaid(nodes)
        assert "graph TD" in mermaid
        assert "handle_request" in mermaid
        assert "call_openai" in mermaid
        assert "<i>LLM</i>" in mermaid
        assert "-->" in mermaid

    def test_root_and_llm_have_distinct_shapes(self) -> None:
        nodes = [
            DagNode(
                name="root",
                code_pointer="f.py:root",
                description="root",
            ),
            DagNode(
                name="child_llm",
                code_pointer="f.py:child",
                description="llm",
                parent="root",
                is_llm_call=True,
            ),
            DagNode(
                name="child_regular",
                code_pointer="f.py:other",
                description="other",
                parent="root",
            ),
        ]
        mermaid = generate_mermaid(nodes)
        assert '(["root"])' in mermaid
        assert '[["child_llm<br/><i>LLM</i>"]]' in mermaid
        assert '["child_regular"]' in mermaid
