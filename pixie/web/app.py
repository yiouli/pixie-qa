"""Starlette application for the pixie web UI.

Serves the single-page React app and provides API endpoints for:
- listing / reading artifacts (markdown, datasets, scorecards)
- SSE stream for live file-change notifications
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncGenerator
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from starlette.routing import Route

logger = logging.getLogger(__name__)


def _resolve_artifact_root(root: str) -> Path:
    """Return the absolute path to the pixie artifact root directory."""
    return Path(root).resolve()


def _list_md_files(root: Path) -> list[dict[str, str]]:
    """Return markdown files sorted by name."""
    files: list[dict[str, str]] = []
    if not root.exists():
        return files
    for p in sorted(root.glob("*.md")):
        files.append({"name": p.name, "path": p.name})
    return files


def _list_datasets(root: Path) -> list[dict[str, str]]:
    """Return dataset JSON files."""
    ds_dir = root / "datasets"
    files: list[dict[str, str]] = []
    if not ds_dir.exists():
        return files
    for p in sorted(ds_dir.glob("*.json")):
        files.append({"name": p.stem, "path": f"datasets/{p.name}"})
    return files


def _list_scorecards(root: Path) -> list[dict[str, str]]:
    """Return scorecard HTML files, newest first."""
    sc_dir = root / "scorecards"
    files: list[dict[str, str]] = []
    if not sc_dir.exists():
        return files
    for p in sorted(sc_dir.glob("*.html"), reverse=True):
        files.append({"name": p.stem, "path": f"scorecards/{p.name}"})
    return files


def _build_manifest(root: Path) -> dict[str, object]:
    """Build a full manifest of all artifacts."""
    return {
        "markdown_files": _list_md_files(root),
        "datasets": _list_datasets(root),
        "scorecards": _list_scorecards(root),
    }


class SSEManager:
    """Manages Server-Sent Events connections and broadcasts."""

    def __init__(self) -> None:
        self._queues: list[asyncio.Queue[str]] = []

    def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue()
        self._queues.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        with contextlib.suppress(ValueError):
            self._queues.remove(q)

    def has_subscribers(self) -> bool:
        return len(self._queues) > 0

    async def broadcast(self, event_type: str, data: object) -> None:
        payload = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        dead: list[asyncio.Queue[str]] = []
        for q in self._queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._queues.remove(q)


def _load_webui_html() -> str:
    """Load the compiled web UI HTML from assets."""
    import importlib.resources

    assets = importlib.resources.files("pixie.assets")
    webui_file = assets.joinpath("webui.html")
    return webui_file.read_text(encoding="utf-8")


def create_app(root: str, sse_manager: SSEManager | None = None) -> Starlette:
    """Create the Starlette web UI application.

    Args:
        root: Path to the pixie artifact root directory.
        sse_manager: Optional SSE manager instance (created if not provided).

    Returns:
        A configured Starlette application.
    """
    artifact_root = _resolve_artifact_root(root)
    sse = sse_manager or SSEManager()

    async def index(request: Request) -> HTMLResponse:
        try:
            html = _load_webui_html()
        except FileNotFoundError:
            return HTMLResponse(
                "<h1>Web UI not built</h1><p>Run <code>cd frontend && npm run build</code></p>",
                status_code=500,
            )
        return HTMLResponse(html)

    async def api_manifest(request: Request) -> JSONResponse:
        manifest = _build_manifest(artifact_root)
        return JSONResponse(manifest)

    async def api_file_content(request: Request) -> Response:
        file_path = request.query_params.get("path", "")
        if not file_path:
            return JSONResponse({"error": "path parameter required"}, status_code=400)

        # Prevent path traversal
        resolved = (artifact_root / file_path).resolve()
        if not str(resolved).startswith(str(artifact_root)):
            return JSONResponse({"error": "invalid path"}, status_code=403)

        if not resolved.exists():
            return JSONResponse({"error": "file not found"}, status_code=404)

        if resolved.suffix == ".json":
            content = resolved.read_text(encoding="utf-8")
            return JSONResponse(json.loads(content))
        elif resolved.suffix == ".html":
            content = resolved.read_text(encoding="utf-8")
            return HTMLResponse(content)
        elif resolved.suffix == ".md":
            content = resolved.read_text(encoding="utf-8")
            return JSONResponse({"content": content})
        else:
            return JSONResponse({"error": "unsupported file type"}, status_code=400)

    async def api_events(request: Request) -> StreamingResponse:
        queue = sse.subscribe()

        async def stream() -> AsyncGenerator[bytes, None]:
            manifest = _build_manifest(artifact_root)
            yield f"event: manifest\ndata: {json.dumps(manifest)}\n\n".encode()

            try:
                while True:
                    payload = await queue.get()
                    yield payload.encode()
            except asyncio.CancelledError:
                pass
            finally:
                sse.unsubscribe(queue)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    routes = [
        Route("/", index),
        Route("/api/manifest", api_manifest),
        Route("/api/file", api_file_content),
        Route("/api/events", api_events),
    ]

    return Starlette(routes=routes)
