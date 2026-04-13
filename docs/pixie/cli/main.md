Module pixie.cli.main
=====================
``pixie`` CLI entry point — top-level command with subcommand routing.

Usage::

    pixie test [path] [-v] [--no-open]
    pixie trace --runnable <ref> --input <file> --output <file>
    pixie format --input <file> --output <file>
    pixie init [root]
    pixie start [root]

Functions
---------

`def main(argv: list[str] | None = None) ‑> int`
:   Entry point for the ``pixie`` command.
    
    Args:
        argv: Command-line arguments. Defaults to ``sys.argv[1:]``.
    
    Returns:
        Exit code: 0 on success, 1 on error.