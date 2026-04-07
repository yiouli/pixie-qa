Module pixie.harness.runnable
=============================
Runnable protocol for dataset-driven evaluation.

Defines the ``Runnable`` protocol that custom runnables implement to
support setup/teardown lifecycle, typed arguments via Pydantic models,
and integration with ``pixie trace`` and ``pixie test``.

Functions
---------

`get_runnable_args_type(runnable_cls: type[Runnable[Any]]) ‑> type[pydantic.main.BaseModel]`
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

`is_runnable_class(obj: Any) ‑> bool`
:   Check whether *obj* is a class that implements the Runnable protocol.
    
    Verifies that *obj* is a class with ``create``, ``run``, and optionally
    ``setup``/``teardown`` methods.

Classes
-------

`Runnable(*args, **kwargs)`
:   Protocol for structured runnables used by the dataset runner.
    
    Implementors define:
    - ``create()`` — class method to construct the runnable instance.
    - ``setup()`` — optional async lifecycle hook called once before all entries.
    - ``teardown()`` — optional async lifecycle hook called once after all entries.
    - ``run(args)`` — execute the runnable with typed Pydantic args.

    ### Ancestors (in MRO)

    * typing.Protocol
    * typing.Generic

    ### Static methods

    `create() ‑> pixie.harness.runnable.Runnable[typing.Any]`
    :   Construct and return a runnable instance.

    ### Methods

    `run(self, args: T) ‑> None`
    :   Execute the runnable with typed arguments.

    `setup(self) ‑> None`
    :   Optional setup before running entries. Default is no-op.

    `teardown(self) ‑> None`
    :   Optional teardown after running entries. Default is no-op.