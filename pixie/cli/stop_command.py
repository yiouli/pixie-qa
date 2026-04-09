"""``pixie stop`` — stop the running web UI server.

Usage::

    pixie stop [root]

Sends a shutdown request to the server and waits for it to exit.
"""

from __future__ import annotations

from pixie.config import get_config
from pixie.web.server import stop_server


def stop(root: str | None = None) -> int:
    """Stop the running pixie web server.

    Args:
        root: Optional explicit artifact root directory.
              Defaults to ``PIXIE_ROOT`` or ``pixie_qa``.

    Returns:
        Exit code (0 on success, 1 if the server did not stop).
    """
    config = get_config()
    artifact_root = root or config.root
    stopped = stop_server(artifact_root)
    if stopped:
        print("Server stopped.")  # noqa: T201
        return 0
    print("Server did not stop within timeout.")  # noqa: T201
    return 1
