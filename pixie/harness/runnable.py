"""Runnable protocol for dataset-driven evaluation.

Defines the ``Runnable`` protocol that custom runnables implement to
support setup/teardown lifecycle, typed arguments via Pydantic models,
and integration with ``pixie trace`` and ``pixie test``.
"""

from __future__ import annotations

import inspect
from typing import Any, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel, contravariant=True)


@runtime_checkable
class Runnable(Protocol[T]):
    """Protocol for structured runnables used by the dataset runner.

    Implementors define:
    - ``create()`` — class method to construct the runnable instance.
    - ``setup()`` — optional async lifecycle hook called once before all entries.
    - ``teardown()`` — optional async lifecycle hook called once after all entries.
    - ``run(args)`` — execute the runnable with typed Pydantic args.
    """

    @classmethod
    def create(cls) -> Runnable[Any]:
        """Construct and return a runnable instance."""
        ...

    async def setup(self) -> None:
        """Optional setup before running entries. Default is no-op."""
        pass

    async def teardown(self) -> None:
        """Optional teardown after running entries. Default is no-op."""
        pass

    async def run(self, args: T) -> None:
        """Execute the runnable with typed arguments."""
        ...


def get_runnable_args_type(runnable_cls: type[Runnable[Any]]) -> type[BaseModel]:
    """Extract the Pydantic model type from the ``run`` method's type hints.

    Inspects the ``run`` method's ``args`` parameter annotation to find
    the concrete ``BaseModel`` subclass used for typed arguments.

    Args:
        runnable_cls: A class implementing the :class:`Runnable` protocol.

    Returns:
        The ``BaseModel`` subclass for the ``args`` parameter.

    Raises:
        TypeError: If the ``args`` parameter has no annotation or the
            annotation is not a ``BaseModel`` subclass.
    """
    run_method = getattr(runnable_cls, "run", None)
    if run_method is None:
        raise TypeError(f"{runnable_cls.__name__} does not have a 'run' method.")

    hints = inspect.get_annotations(run_method, eval_str=True)
    args_type = hints.get("args")
    if args_type is None:
        raise TypeError(
            f"{runnable_cls.__name__}.run() must have a type-annotated 'args' parameter."
        )

    if not (isinstance(args_type, type) and issubclass(args_type, BaseModel)):
        raise TypeError(
            f"{runnable_cls.__name__}.run() 'args' must be a BaseModel subclass, "
            f"got {args_type!r}."
        )

    return args_type


def is_runnable_class(obj: Any) -> bool:
    """Check whether *obj* is a class that implements the Runnable protocol.

    Verifies that *obj* is a class with ``create``, ``run``, and optionally
    ``setup``/``teardown`` methods.
    """
    if not isinstance(obj, type):
        return False
    return (
        hasattr(obj, "create")
        and hasattr(obj, "run")
        and callable(getattr(obj, "create", None))
        and callable(getattr(obj, "run", None))
    )
