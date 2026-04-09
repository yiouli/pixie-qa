Module pixie.cli.stop_command
=============================
``pixie stop`` — stop the running web UI server.

Usage::

    pixie stop [root]

Sends a shutdown request to the server and waits for it to exit.

Functions
---------

`def stop(root: str | None = None) ‑> int`
:   Stop the running pixie web server.
    
    Args:
        root: Optional explicit artifact root directory.
              Defaults to ``PIXIE_ROOT`` or ``pixie_qa``.
    
    Returns:
        Exit code (0 on success, 1 if the server did not stop).