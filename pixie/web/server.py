"""Server runner for the pixie web UI.

Starts the Starlette app with uvicorn, launches the file watcher,
and optionally opens the browser.

A ``server.lock`` file is written to the pixie artifact root on startup
(containing the port number) and removed on shutdown.  Other processes
(e.g. ``open_webui`` or ``pixie test``) read this file to discover whether
the server is already running and on which port.
"""

from __future__ import annotations

import asyncio
import atexit
import contextlib
import json
import logging
import socket
import threading
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path

import uvicorn

from pixie.web.app import SSEManager, create_app
from pixie.web.watcher import watch_artifacts

logger = logging.getLogger(__name__)

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 7118

#: Name of the lock file placed in the pixie artifact root.
_LOCK_FILENAME = "server.lock"


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


def _lock_path(root: str) -> Path:
    """Return the path to the server lock file for *root*."""
    return Path(root).resolve() / _LOCK_FILENAME


def _write_lock(root: str, port: int) -> None:
    """Write the server lock file containing the port number."""
    path = _lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(port))


def _remove_lock(root: str) -> None:
    """Remove the server lock file if it exists."""
    with contextlib.suppress(FileNotFoundError):
        _lock_path(root).unlink()


def _read_lock(root: str) -> int | None:
    """Read the port from the server lock file.

    Returns:
        The port number if the lock file exists, otherwise *None*.
    """
    path = _lock_path(root)
    try:
        return int(path.read_text().strip())
    except (FileNotFoundError, ValueError):
        return None


@dataclass(frozen=True)
class ServerStatus:
    """Status of the pixie web server for a given root."""

    running: bool
    port: int | None
    active_clients: int


def _probe_server(host: str, port: int) -> int | None:
    """Probe the server's ``/api/status`` endpoint.

    Returns:
        The active client count if the server responds, otherwise *None*.
    """
    url = f"http://{host}:{port}/api/status"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode())
            return int(data.get("active_clients", 0))
    except Exception:  # noqa: BLE001 — network errors, timeouts, etc.
        return None


def _send_navigate(
    host: str,
    port: int,
    *,
    tab: str | None = None,
    item_id: str | None = None,
) -> bool:
    """Ask the running server to broadcast a ``navigate`` SSE event.

    Returns *True* if the request succeeded, *False* otherwise.
    """
    from urllib.parse import quote, urlencode

    params: dict[str, str] = {}
    if tab:
        params["tab"] = tab
    if item_id:
        params["id"] = item_id
    if not params:
        return False
    url = f"http://{host}:{port}/api/navigate?{urlencode(params, quote_via=quote)}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return int(resp.status) == 200
    except Exception:  # noqa: BLE001
        return False


def _is_server_running(root: str, host: str = _DEFAULT_HOST) -> int | None:
    """Check whether a pixie server is running for *root*.

    Reads the lock file and probes the ``/api/status`` endpoint to
    verify the server is actually alive (not just a stale lock file
    or another process on the same port).

    Returns:
        The port number if the server is running, otherwise *None*.
    """
    port = _read_lock(root)
    if port is None:
        return None
    if _probe_server(host, port) is not None:
        return port
    # Stale lock — clean it up
    _remove_lock(root)
    return None


def get_server_status(root: str, host: str = _DEFAULT_HOST) -> ServerStatus:
    """Return the status of the pixie web server for *root*.

    Checks the lock file and probes the ``/api/status`` endpoint.
    """
    port = _read_lock(root)
    if port is None:
        return ServerStatus(running=False, port=None, active_clients=0)
    active_clients = _probe_server(host, port)
    if active_clients is None:
        _remove_lock(root)
        return ServerStatus(running=False, port=None, active_clients=0)
    return ServerStatus(running=True, port=port, active_clients=active_clients)


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

    Writes a ``server.lock`` to *root* on startup and removes it on
    shutdown so other processes can discover whether the server is
    already running.

    Args:
        root: Path to the pixie artifact root directory.
        host: Host to bind to.
        port: Port to bind to.
        open_browser: Whether to open the browser on startup.
        tab: Optional tab to pre-select in the web UI.
        item_id: Optional item path to pre-select within the tab.
    """
    # Check if a server is already running for this root
    running_port = _is_server_running(root, host)
    if running_port is not None:
        url = build_url(host, running_port, tab=tab, item_id=item_id)
        print(f"Server already running on port {running_port}: {url}")
        logger.info("Server already running on port %d", running_port)
        if open_browser:
            # Send navigate event to update any existing browser tabs…
            _send_navigate(host, running_port, tab=tab, item_id=item_id)
            # …and always open the browser so the user sees the UI.
            webbrowser.open(url)
        return

    # If the default port is taken by something else, find another
    if _is_port_in_use(host, port):
        port = _find_open_port(host, port + 1)

    sse_manager = SSEManager()

    _server_ref: uvicorn.Server | None = None

    def _request_shutdown() -> None:
        if _server_ref is not None:
            _server_ref.should_exit = True

    app = create_app(root, sse_manager=sse_manager, shutdown_callback=_request_shutdown)

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    _server_ref = server

    _write_lock(root, port)

    # Register atexit handler for lock cleanup (belt-and-suspenders)
    atexit.register(_remove_lock, root)

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
            _remove_lock(root)
            watcher_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await watcher_task

    try:
        asyncio.run(_run())
    finally:
        # Belt-and-suspenders: ensure lock is removed even on unexpected exit
        _remove_lock(root)


def open_webui(
    root: str,
    *,
    host: str = _DEFAULT_HOST,
    port: int = _DEFAULT_PORT,
    tab: str | None = None,
    item_id: str | None = None,
) -> None:
    """Open the web UI, starting the server in the background if needed.

    Checks the ``server.lock`` file in *root* to discover whether a
    server is already running (and on which port).  If it is, opens
    the browser.  Otherwise, starts the server on a daemon thread and
    opens the browser.

    This function returns immediately in both cases.

    Args:
        root: Path to the pixie artifact root directory.
        host: Host to bind to.
        port: Port to bind to (used as default when no lock file exists).
        tab: Optional tab to pre-select in the web UI.
        item_id: Optional item path to pre-select within the tab.
    """
    running_port = _is_server_running(root, host)
    if running_port is not None:
        active = _probe_server(host, running_port)
        if active and active > 0:
            # Existing clients — send navigate event instead of new tab
            logger.info(
                "Server on port %d has %d active client(s), sending navigate",
                running_port,
                active,
            )
            _send_navigate(host, running_port, tab=tab, item_id=item_id)
        else:
            url = build_url(host, running_port, tab=tab, item_id=item_id)
            logger.info(
                "Server on port %d has no active clients, opening browser",
                running_port,
            )
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

    # Read the actual port from the lock file (may differ from default)
    actual_port = _read_lock(root) or port
    url = build_url(host, actual_port, tab=tab, item_id=item_id)
    logger.info("Opening browser at %s", url)
    webbrowser.open(url)


def _send_shutdown(host: str, port: int) -> bool:
    """Send a POST request to the server's ``/api/shutdown`` endpoint.

    Returns *True* if the server acknowledged the request.
    """
    url = f"http://{host}:{port}/api/shutdown"
    try:
        req = urllib.request.Request(url, method="POST", data=b"")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return int(resp.status) == 200
    except Exception:  # noqa: BLE001
        return False


def _wait_for_server(root: str, host: str, timeout: float = 5.0) -> int | None:
    """Poll until the server is reachable or *timeout* seconds elapse.

    Returns:
        The port number if the server becomes reachable, otherwise *None*.
    """
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        port = _is_server_running(root, host)
        if port is not None:
            return port
        time.sleep(0.2)
    return None


def start_detached(
    root: str,
    *,
    host: str = _DEFAULT_HOST,
    port: int = _DEFAULT_PORT,
    open_browser: bool = True,
    tab: str | None = None,
    item_id: str | None = None,
) -> int | None:
    """Start the server in a detached subprocess and return immediately.

    If a server is already running for *root*, reuses it (optionally
    opening the browser / sending a navigate event).

    Args:
        root: Pixie artifact root directory.
        host: Host to bind to.
        port: Preferred port.
        open_browser: Whether to open the browser after the server starts.
        tab: Optional tab to pre-select.
        item_id: Optional item path to pre-select.

    Returns:
        The port the server is listening on, or *None* if it failed to
        start within the timeout window.
    """
    import subprocess
    import sys

    # Re-use an existing server
    running_port = _is_server_running(root, host)
    if running_port is not None:
        logger.info("Server already running on port %d", running_port)
        if open_browser:
            _send_navigate(host, running_port, tab=tab, item_id=item_id)
            webbrowser.open(build_url(host, running_port, tab=tab, item_id=item_id))
        return running_port

    # Spawn a new detached process running `python -m pixie.web._serve`
    cmd = [
        sys.executable,
        "-m",
        "pixie.web._serve",
        root,
        "--host",
        host,
        "--port",
        str(port),
    ]

    # Write stderr to a log file so startup failures are diagnosable
    log_path = Path(root).resolve() / "server.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("w")

    # Detach: new session, redirect stdio
    proc = subprocess.Popen(
        cmd,
        start_new_session=True,
        stdout=log_file,
        stderr=log_file,
        stdin=subprocess.DEVNULL,
    )

    # Wait for the server to become reachable (15s to handle slow envs)
    actual_port = _wait_for_server(root, host, timeout=15.0)
    if actual_port is None:
        # Check if the process already exited (crash on startup)
        retcode = proc.poll()
        log_file.close()
        stderr_tail = ""
        with contextlib.suppress(Exception):
            text = log_path.read_text().strip()
            # Show last 20 lines of the log for diagnostics
            lines = text.splitlines()
            stderr_tail = "\n".join(lines[-20:])
        if retcode is not None:
            logger.warning(
                "Server process exited with code %d before becoming reachable",
                retcode,
            )
        else:
            logger.warning("Server did not start within timeout")
        if stderr_tail:
            logger.warning("Server log tail:\n%s", stderr_tail)
        return None
    log_file.close()

    if open_browser:
        webbrowser.open(build_url(host, actual_port, tab=tab, item_id=item_id))

    return actual_port


def stop_server(root: str, host: str = _DEFAULT_HOST) -> bool:
    """Stop a running server for *root* by requesting graceful shutdown.

    Sends a POST to ``/api/shutdown`` and waits briefly for the process
    to exit and the lock file to disappear.

    Returns:
        *True* if the server was stopped (or was not running).
    """
    import time

    port = _is_server_running(root, host)
    if port is None:
        return True  # nothing to stop

    _send_shutdown(host, port)

    # Wait for lock file to disappear (server cleans up on exit)
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if _is_server_running(root, host) is None:
            return True
        time.sleep(0.2)

    logger.warning("Server on port %d did not stop within timeout", port)
    return False


def ensure_server(root: str, host: str = _DEFAULT_HOST) -> int | None:
    """Ensure a server is running for *root*, starting one if needed.

    Unlike :func:`start_detached`, this never opens the browser.

    Returns:
        The port number if a server is running, otherwise *None*.
    """
    running_port = _is_server_running(root, host)
    if running_port is not None:
        return running_port
    return start_detached(root, host=host, open_browser=False)
