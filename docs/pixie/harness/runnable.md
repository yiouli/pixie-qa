Module pixie.harness.runnable
=============================
Runnable protocol for dataset-driven evaluation.

Defines the ``Runnable`` protocol that custom runnables implement to
support setup/teardown lifecycle, typed arguments via Pydantic models,
and integration with ``pixie trace`` and ``pixie test``.

Functions
---------

`def get_runnable_args_type(runnable_cls: type[Runnable[Any]]) ‑> type[pydantic.main.BaseModel]`
:   Extract the Pydantic model type from the ``run`` method's type hints.
    
    Inspects the ``run`` method's ``args`` parameter annotation to find
    the concrete ``BaseModel`` subclass used for typed arguments.
    
    Args:
        runnable_cls: A class implementing the :class:`Runnable` protocol.
    
    Returns:
        The ``BaseModel`` subclass for the ``args`` parameter.
    
    Raises:
        TypeError: If the ``args`` parameter has no annotation or the
            annotation is not a ``BaseModel`` subclass.

`def is_runnable_class(obj: Any) ‑> bool`
:   Check whether *obj* is a class that implements the Runnable protocol.
    
    Verifies that *obj* is a class with ``create``, ``run``, and optionally
    ``setup``/``teardown`` methods.

Classes
-------

`Runnable(*args, **kwargs)`
:   Protocol for structured runnables used by the dataset runner.
    
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

    ### Ancestors (in MRO)

    * typing.Protocol
    * typing.Generic

    ### Static methods

    `def create() ‑> pixie.harness.runnable.Runnable[typing.Any]`
    :   Construct and return a runnable instance.

    ### Methods

    `async def run(self, args: T) ‑> None`
    :   Execute the runnable with typed arguments.
        
        Called concurrently for each dataset entry.  Must be safe for
        concurrent execution — see class docstring for details.

    `async def setup(self) ‑> None`
    :   Optional setup before running entries. Default is no-op.

    `async def teardown(self) ‑> None`
    :   Optional teardown after running entries. Default is no-op.