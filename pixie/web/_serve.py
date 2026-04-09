"""Subprocess entry point for the pixie web server.

Run as::

    python -m pixie.web._serve <root> [--host HOST] [--port PORT]

This module is invoked by :func:`pixie.web.server.start_detached` in a
detached process so the server keeps running after the parent exits.
"""

from __future__ import annotations

import argparse

from pixie.web.server import _DEFAULT_HOST, _DEFAULT_PORT, run_server


def _main() -> None:
    parser = argparse.ArgumentParser(prog="pixie.web._serve")
    parser.add_argument("root", help="Pixie artifact root directory")
    parser.add_argument("--host", default=_DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=_DEFAULT_PORT)
    args = parser.parse_args()

    run_server(
        args.root,
        host=args.host,
        port=args.port,
        open_browser=False,
    )


if __name__ == "__main__":
    _main()
