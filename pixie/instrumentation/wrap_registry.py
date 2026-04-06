from __future__ import annotations

from contextvars import ContextVar
from typing import Any

# Input registry: populated by test runner before each eval run
# Keys are wrap names, values are jsonpickle-serialized strings
_input_registry: ContextVar[dict[str, str] | None] = ContextVar(
    "_input_registry", default=None
)

# Capture registry: populated by wrap() during eval runs for output/state
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
    """Get the capture registry for output/state values."""
    return _capture_registry.get()


def init_capture_registry() -> dict[str, Any]:
    """Initialize and return a fresh capture registry."""
    reg: dict[str, Any] = {}
    _capture_registry.set(reg)
    return reg


def clear_capture_registry() -> None:
    """Clear the capture registry."""
    _capture_registry.set(None)
