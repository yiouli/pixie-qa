Module pixie.web.app
====================
Starlette application for the pixie web UI.

Serves the single-page React app and provides API endpoints for:
- listing / reading artifacts (markdown, datasets, scorecards)
- SSE stream for live file-change notifications

Functions
---------

`create_app(root: str, sse_manager: SSEManager | None = None) ‑> starlette.applications.Starlette`
:   Create the Starlette web UI application.
    
    Args:
        root: Path to the pixie artifact root directory.
        sse_manager: Optional SSE manager instance (created if not provided).
    
    Returns:
        A configured Starlette application.

Classes
-------

`SSEManager()`
:   Manages Server-Sent Events connections and broadcasts.

    ### Instance variables

    `subscriber_count: int`
    :

    ### Methods

    `broadcast(self, event_type: str, data: object) ‑> None`
    :

    `has_subscribers(self) ‑> bool`
    :

    `subscribe(self) ‑> asyncio.queues.Queue[str]`
    :

    `unsubscribe(self, q: asyncio.Queue[str]) ‑> None`
    :