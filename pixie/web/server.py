"""Server runner for the pixie web UI.

Starts the Starlette app with uvicorn, launches the file watcher,
and optionally opens the browser.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import socket
import threading
import webbrowser

import uvicorn

from pixie.web.app import SSEManager, create_app
from pixie.web.watcher import watch_artifacts

logger = logging.getLogger(__name__)

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 7118


def build_url(
    host: str = _DEFAULT_HOST,
    port: int = _DEFAULT_PORT,
    *,
    tab: str | None = None,
    item_id: str | None = None,
) -> str:
    """Build the web UI URL with optional query parameters.

    Args:
        host: Server host.
        port: Server port.
        tab: Optional tab to select (e.g. "scorecards", "datasets").
        item_id: Optional item path to select within the tab.

    Returns:
        Full URL string.
    """
    url = f"http://{host}:{port}"
    params: list[str] = []
    if tab:
        params.append(f"tab={tab}")
    if item_id:
        from urllib.parse import quote

        params.append(f"id={quote(item_id, safe='/')}")
    if params:
        url += "?" + "&".join(params)
    return url


def _find_open_port(host: str, start_port: int) -> int:
    """Find an open port starting from start_port."""
    port = start_port
    while port < start_port + 100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                port += 1
    return start_port


def _is_port_in_use(host: str, port: int) -> bool:
    """Check whether a port is already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def run_server(
    root: str,
    *,
    host: str = _DEFAULT_HOST,
    port: int = _DEFAULT_PORT,
    open_browser: bool = True,
    tab: str | None = None,
    item_id: str | None = None,
) -> None:
    """Start the pixie web UI server.

    Args:
        root: Path to the pixie artifact root directory.
        host: Host to bind to.
        port: Port to bind to.
        open_browser: Whether to open the browser on startup.
        tab: Optional tab to pre-select in the web UI.
        item_id: Optional item path to pre-select within the tab.
    """
    # If default port is taken, find another
    if _is_port_in_use(host, port):
        logger.info("Port %d in use, a server may already be running", port)
        if open_browser:
            webbrowser.open(build_url(host, port, tab=tab, item_id=item_id))
        return

    sse_manager = SSEManager()
    app = create_app(root, sse_manager=sse_manager)

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)

    async def _run() -> None:
        # Start file watcher as a background task
        watcher_task = asyncio.create_task(watch_artifacts(root, sse_manager))

        if open_browser:
            # Open browser after a short delay to let the server start
            async def _open_browser() -> None:
                await asyncio.sleep(0.5)
                url = build_url(host, port, tab=tab, item_id=item_id)
                logger.info("Opening browser at %s", url)
                webbrowser.open(url)

            asyncio.create_task(_open_browser())

        try:
            await server.serve()
        finally:
            watcher_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await watcher_task

    asyncio.run(_run())


def open_webui(
    root: str,
    *,
    host: str = _DEFAULT_HOST,
    port: int = _DEFAULT_PORT,
    tab: str | None = None,
    item_id: str | None = None,
) -> None:
    """Open the web UI, starting the server in the background if needed.

    If the server is already running on *port*, opens the browser to it.
    Otherwise, starts the server on a daemon thread and opens the browser.

    This function returns immediately in both cases.

    Args:
        root: Path to the pixie artifact root directory.
        host: Host to bind to.
        port: Port to bind to.
        tab: Optional tab to pre-select in the web UI.
        item_id: Optional item path to pre-select within the tab.
    """
    url = build_url(host, port, tab=tab, item_id=item_id)

    if _is_port_in_use(host, port):
        logger.info("Server already running on port %d, opening browser", port)
        webbrowser.open(url)
        return

    # Start the server on a daemon thread so the caller is not blocked
    thread = threading.Thread(
        target=run_server,
        args=(root,),
        kwargs={
            "host": host,
            "port": port,
            "open_browser": False,  # we open the browser ourselves
            "tab": tab,
            "item_id": item_id,
        },
        daemon=True,
    )
    thread.start()

    # Give the server a moment to bind, then open the browser
    import time

    time.sleep(0.8)
    logger.info("Opening browser at %s", url)
    webbrowser.open(url)
