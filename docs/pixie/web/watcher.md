Module pixie.web.watcher
========================
File watcher for pixie artifact directories.

Uses ``watchfiles`` to monitor the pixie root for artifact changes
(markdown, datasets, scorecards) and pushes SSE events to all subscribers.

Functions
---------

`watch_artifacts(root: str, sse: SSEManager) ‑> None`
:   Watch the artifact root for changes and broadcast SSE events.
    
    This coroutine runs indefinitely (until cancelled). It watches the root
    directory (plus ``datasets/`` and ``scorecards/`` subdirectories) for
    file additions, modifications, and deletions.
    
    On any relevant change it broadcasts two SSE events:
    1. ``file_change`` — details about the specific change
    2. ``manifest`` — the full updated manifest
    
    Args:
        root: Path to the pixie artifact root directory.
        sse: SSE manager to broadcast events through.