Module pixie.web.server
=======================
Server runner for the pixie web UI.

Starts the Starlette app with uvicorn, launches the file watcher,
and optionally opens the browser.

A ``server.lock`` file is written to the pixie artifact root on startup
(containing the port number) and removed on shutdown.  Other processes
(e.g. ``open_webui`` or ``pixie test``) read this file to discover whether
the server is already running and on which port.

Functions
---------

`def build_url(host: str = '127.0.0.1', port: int = 7118, *, tab: str | None = None, item_id: str | None = None) ‑> str`
:   Build the web UI URL with optional query parameters.
    
    Args:
        host: Server host.
        port: Server port.
        tab: Optional tab to select (e.g. "scorecards", "datasets").
        item_id: Optional item path to select within the tab.
    
    Returns:
        Full URL string.

`def get_server_status(root: str, host: str = '127.0.0.1') ‑> pixie.web.server.ServerStatus`
:   Return the status of the pixie web server for *root*.
    
    Checks the lock file and probes the ``/api/status`` endpoint.

`def open_webui(root: str, *, host: str = '127.0.0.1', port: int = 7118, tab: str | None = None, item_id: str | None = None) ‑> None`
:   Open the web UI, starting the server in the background if needed.
    
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

`def run_server(root: str, *, host: str = '127.0.0.1', port: int = 7118, open_browser: bool = True, tab: str | None = None, item_id: str | None = None) ‑> None`
:   Start the pixie web UI server.
    
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

Classes
-------

`ServerStatus(running: bool, port: int | None, active_clients: int)`
:   Status of the pixie web server for a given root.

    ### Instance variables

    `active_clients: int`
    :

    `port: int | None`
    :

    `running: bool`
    :