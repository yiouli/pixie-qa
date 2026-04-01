"""File watcher for pixie artifact directories.

Uses ``watchfiles`` to monitor the pixie root for artifact changes
(markdown, datasets, scorecards) and pushes SSE events to all subscribers.
"""

from __future__ import annotations

import logging
from pathlib import Path

from watchfiles import Change, awatch

from pixie.web.app import SSEManager, _build_manifest

logger = logging.getLogger(__name__)

#: File patterns we care about
_WATCHED_SUFFIXES = {".md", ".json", ".html"}


def _is_artifact(path: Path, root: Path) -> bool:
    """Return True if the path is a relevant artifact file."""
    if path.suffix not in _WATCHED_SUFFIXES:
        return False
    rel = path.relative_to(root)
    parts = rel.parts
    # Top-level .md files
    if len(parts) == 1 and path.suffix == ".md":
        return True
    # datasets/*.json
    if len(parts) == 2 and parts[0] == "datasets" and path.suffix == ".json":
        return True
    # scorecards/*.html
    return len(parts) == 2 and parts[0] == "scorecards" and path.suffix == ".html"


def _change_label(change: Change) -> str:
    """Return a human-readable label for a watchfiles Change."""
    if change == Change.added:
        return "added"
    elif change == Change.modified:
        return "modified"
    elif change == Change.deleted:
        return "deleted"
    return "unknown"


async def watch_artifacts(root: str, sse: SSEManager) -> None:
    """Watch the artifact root for changes and broadcast SSE events.

    This coroutine runs indefinitely (until cancelled). It watches the root
    directory (plus ``datasets/`` and ``scorecards/`` subdirectories) for
    file additions, modifications, and deletions.

    On any relevant change it broadcasts two SSE events:
    1. ``file_change`` — details about the specific change
    2. ``manifest`` — the full updated manifest

    Args:
        root: Path to the pixie artifact root directory.
        sse: SSE manager to broadcast events through.
    """
    root_path = Path(root).resolve()

    # Ensure watched directories exist
    root_path.mkdir(parents=True, exist_ok=True)
    (root_path / "datasets").mkdir(exist_ok=True)
    (root_path / "scorecards").mkdir(exist_ok=True)

    logger.info("Watching for artifact changes in %s", root_path)

    async for changes in awatch(root_path):
        relevant_changes: list[dict[str, str]] = []
        for change, path_str in changes:
            path = Path(path_str)
            try:
                if _is_artifact(path, root_path):
                    relevant_changes.append(
                        {
                            "type": _change_label(change),
                            "path": str(path.relative_to(root_path)),
                        }
                    )
            except ValueError:
                # path is outside root_path — ignore
                continue

        if relevant_changes:
            logger.debug("Artifact changes: %s", relevant_changes)
            await sse.broadcast("file_change", relevant_changes)
            manifest = _build_manifest(root_path)
            await sse.broadcast("manifest", manifest)
