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

    Lifecycle:

    1. ``create()`` — class method; constructs a single runnable instance.
    2. ``setup()`` — called **once** before any entries run.
    3. ``run(args)`` — called **concurrently** for each dataset entry
       (up to 4 entries in parallel by default).
    4. ``teardown()`` — called **once** after all entries finish.

    .. important::

       ``run()`` **must be concurrency-safe**.  Multiple ``run()`` calls
       execute concurrently via ``asyncio.gather``.  If your implementation
       uses shared mutable state (database connections, file handles, in-memory
       caches), you must synchronise access — for example with
       ``asyncio.Semaphore`` or ``asyncio.Lock``::

           class AppRunnable(pixie.Runnable[AppArgs]):
               _sem: asyncio.Semaphore

               @classmethod
               def create(cls) -> AppRunnable:
                   inst = cls()
                   inst._sem = asyncio.Semaphore(1)  # serialise if needed
                   return inst

               async def run(self, args: AppArgs) -> None:
                   async with self._sem:
                       await call_app(args.message)

       Common concurrency pitfalls:

       - **SQLite**: the default ``sqlite3`` connection is not thread-safe and
         does not support concurrent async writes.  Use a ``Semaphore(1)`` or
         switch to ``aiosqlite`` with WAL mode.
       - **Shared HTTP clients**: ``httpx.AsyncClient`` is safe to share, but
         rate-limited APIs may need a semaphore to avoid 429 errors.
       - **Global mutable state**: module-level dicts, lists, or counters
         modified in ``run()`` must be protected.
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
        """Execute the runnable with typed arguments.

        Called concurrently for each dataset entry.  Must be safe for
        concurrent execution — see class docstring for details.
        """
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
