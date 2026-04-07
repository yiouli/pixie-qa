"""Shared utility for running a Runnable with tracing support.

Provides :func:`run_runnable` — used by both ``pixie trace`` and
``pixie test`` to create, setup, run, and teardown a Runnable instance
while optionally logging kwargs to the trace log.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pixie.eval.dataset_runner import _load_callable
from pixie.harness.runnable import get_runnable_args_type, is_runnable_class


def resolve_runnable_reference(reference: str) -> Any:
    """Load a runnable from a ``filepath:callable_name`` reference.

    Args:
        reference: Reference in ``filepath:callable_name`` format.

    Returns:
        The resolved Python object (class or callable).

    Raises:
        ValueError: If *reference* is not in ``filepath:name`` format.
    """
    reference = reference.strip()
    if ":" not in reference:
        raise ValueError(
            f"Runnable must use filepath:name format "
            f"(e.g. 'pixie_qa/scripts/run_app.py:MyRunnable'), "
            f"got {reference!r}."
        )
    return _load_callable(reference, Path.cwd())


async def run_runnable(
    reference: str,
    kwargs: dict[str, Any],
) -> None:
    """Resolve, create, and run a Runnable with the given kwargs.

    Handles the full lifecycle: ``create()`` → ``setup()`` → ``run(args)``
    → ``teardown()``.

    For plain callables (non-Runnable), calls directly with kwargs dict.

    Args:
        reference: ``filepath:callable_name`` reference to the runnable.
        kwargs: Arguments to pass to the runnable.
    """
    resolved = resolve_runnable_reference(reference)

    if is_runnable_class(resolved):
        assert isinstance(resolved, type)
        args_type = get_runnable_args_type(resolved)
        instance = resolved.create()  # type: ignore[attr-defined]
        try:
            await instance.setup()
            args = args_type.model_validate(kwargs)
            await instance.run(args)
        finally:
            await instance.teardown()
    else:
        # Plain callable — call with kwargs dict
        import inspect

        if inspect.iscoroutinefunction(resolved):
            await resolved(kwargs)
        else:
            resolved(kwargs)


def load_input_kwargs(input_path: str | Path) -> dict[str, Any]:
    """Load kwargs from a JSON file.

    Args:
        input_path: Path to a JSON file containing kwargs.

    Returns:
        The parsed kwargs dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the JSON is invalid or not a dict.
    """
    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(
            f"Input file must contain a JSON object, got {type(data).__name__}."
        )

    return data
