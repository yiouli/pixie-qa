"""Context-variable registries for wrap() input injection and output capture.

The input registry is populated by the test runner before each eval run with
dependency data keyed by wrap name.  The capture registries collect output and
state values produced by wrap() during eval runs, for evaluator assessment.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

# Input registry: populated by test runner before each eval run
# Keys are wrap names, values are jsonpickle-serialized strings
_input_registry: ContextVar[dict[str, str] | None] = ContextVar(
    "_input_registry", default=None
)

# Output capture registry: populated by wrap(purpose="output") during eval
_output_capture_registry: ContextVar[dict[str, Any] | None] = ContextVar(
    "_output_capture_registry", default=None
)

# State capture registry: populated by wrap(purpose="state") during eval
_state_capture_registry: ContextVar[dict[str, Any] | None] = ContextVar(
    "_state_capture_registry", default=None
)

# Legacy combined capture registry for backward compatibility
_capture_registry: ContextVar[dict[str, Any] | None] = ContextVar(
    "_capture_registry", default=None
)


def set_input_registry(registry: dict[str, str]) -> None:
    """Set the input registry for the current eval run context."""
    _input_registry.set(registry)


def get_input_registry() -> dict[str, str] | None:
    """Get the input registry, or None if not in eval mode."""
    return _input_registry.get()


def clear_input_registry() -> None:
    """Clear the input registry after an eval run."""
    _input_registry.set(None)


def get_capture_registry() -> dict[str, Any] | None:
    """Get the combined capture registry for output/state values."""
    return _capture_registry.get()


def get_output_capture_registry() -> dict[str, Any] | None:
    """Get the output capture registry (purpose='output' only)."""
    return _output_capture_registry.get()


def get_state_capture_registry() -> dict[str, Any] | None:
    """Get the state capture registry (purpose='state' only)."""
    return _state_capture_registry.get()


def init_capture_registry() -> dict[str, Any]:
    """Initialize and return fresh capture registries.

    Returns the combined legacy registry for backward compatibility.
    """
    combined: dict[str, Any] = {}
    _capture_registry.set(combined)
    _output_capture_registry.set({})
    _state_capture_registry.set({})
    return combined


def clear_capture_registry() -> None:
    """Clear all capture registries."""
    _capture_registry.set(None)
    _output_capture_registry.set(None)
    _state_capture_registry.set(None)
