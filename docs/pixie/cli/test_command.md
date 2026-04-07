Module pixie.cli.test_command
=============================
``pixie test`` CLI entry point.

Usage::

    pixie test [path] [--verbose] [--no-open]

Supports dataset-driven mode — each dataset JSON file specifies its evaluators per row.

Functions
---------

`def main(argv: list[str] | None = None) ‑> int`
:   Entry point for ``pixie test`` command.
    
    Args:
        argv: Command-line arguments. Defaults to ``sys.argv[1:]``.
    
    Returns:
        Exit code: 0 if all tests pass, 1 otherwise.