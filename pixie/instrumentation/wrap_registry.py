"""Context-variable registries for wrap() eval mode.

Two context variables control wrap() behaviour during eval runs:

* ``eval_input`` — populated by the dataset runner before each entry with
  dependency data keyed by wrap name (jsonpickle-serialised strings).
  ``wrap(purpose="input")`` reads from this registry to inject values.
* ``eval_output`` — initialised to an empty list before each entry.
  The ``EvalCaptureLogProcessor`` appends wrap event bodies here so that
  the test runner can collect them into ``Evaluable.eval_output``.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

# Input registry: populated by test runner before each eval run.
# Keys are wrap names, values are jsonpickle-serialised strings.
_eval_input: ContextVar[dict[str, str] | None] = ContextVar(
    "_eval_input", default=None
)

# Output list: each dict is the body of a wrap event (output/state).
_eval_output: ContextVar[list[dict[str, Any]] | None] = ContextVar(
    "_eval_output", default=None
)


def set_eval_input(registry: dict[str, str]) -> None:
    """Set the eval input registry for the current context."""
    _eval_input.set(registry)


def get_eval_input() -> dict[str, str] | None:
    """Get the eval input registry, or ``None`` if not in eval mode."""
    return _eval_input.get()


def clear_eval_input() -> None:
    """Clear the eval input registry."""
    _eval_input.set(None)


def init_eval_output() -> list[dict[str, Any]]:
    """Initialise and return a fresh eval output list."""
    out: list[dict[str, Any]] = []
    _eval_output.set(out)
    return out


def get_eval_output() -> list[dict[str, Any]] | None:
    """Get the eval output list, or ``None`` if not initialised."""
    return _eval_output.get()


def clear_eval_output() -> None:
    """Clear the eval output list."""
    _eval_output.set(None)
