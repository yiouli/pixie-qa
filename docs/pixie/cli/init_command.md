Module pixie.cli.init_command
=============================
``pixie init`` — scaffold the pixie_qa working directory.

Creates the standard directory layout for eval-driven development::

    pixie_qa/
        datasets/
        tests/
        scripts/

The command is idempotent: existing files and directories are never
overwritten or deleted.  Running ``pixie init`` on an already-initialised
project is a safe no-op.

Functions
---------

`init_pixie_dir(root: str | None = None) ‑> pathlib.Path`
:   Create the pixie working directory and its standard layout.
    
    Args:
        root: Override for the pixie root directory.  When *None*,
              uses the value from :func:`pixie.config.get_config`
              (respects ``PIXIE_ROOT`` env var, defaults to ``pixie_qa``).
    
    Returns:
        The resolved :class:`~pathlib.Path` of the root directory.