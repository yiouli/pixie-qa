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
from collections.abc import AsyncGenerator, Callable
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from starlette.routing import Route

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JSONL helpers for api_result
# ---------------------------------------------------------------------------


def _read_jsonl_file(path: Path) -> list[dict[str, object]]:
    """Read a JSONL file and return a list of dicts.  Returns [] if missing."""
    if not path.is_file():
        return []
    items: list[dict[str, object]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def _collapse_named_items(items: list[dict[str, object]]) -> object:
    """Collapse a list of ``{"name": ..., "value": ...}`` dicts for display.

    Empty → ``None``, single item → its value, multiple → ``{name: value}`` dict.
    """
    if not items:
        return None
    if len(items) == 1:
        return items[0].get("value")
    return {str(item.get("name", "")): item.get("value") for item in items}


# ---------------------------------------------------------------------------


def _resolve_artifact_root(root: str) -> Path:
    """Return the absolute path to the pixie artifact root directory."""
    return Path(root).resolve()


def _list_md_files(root: Path) -> list[dict[str, str]]:
    """Return project context files sorted by name.

    Includes markdown files, root-level JSON/JSONL files, and Python files
    (excluding __init__.py).
    """
    files: list[dict[str, str]] = []
    if not root.exists():
        return files
    for p in sorted(root.iterdir()):
        if not p.is_file():
            continue
        if (
            p.suffix == ".md"
            or p.suffix in (".json", ".jsonl")
            or p.suffix == ".py"
            and p.name != "__init__.py"
        ):
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


def _list_results(root: Path) -> list[dict[str, str]]:
    """Return test result directories, newest first."""
    results_dir = root / "results"
    dirs: list[dict[str, str]] = []
    if not results_dir.exists():
        return dirs
    for p in sorted(results_dir.iterdir(), reverse=True):
        if p.is_dir() and (p / "meta.json").exists():
            dirs.append({"name": p.name, "path": f"results/{p.name}"})
    return dirs


def _build_manifest(root: Path) -> dict[str, object]:
    """Build a full manifest of all artifacts."""
    return {
        "markdown_files": _list_md_files(root),
        "datasets": _list_datasets(root),
        "scorecards": _list_scorecards(root),
        "results": _list_results(root),
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

    @property
    def subscriber_count(self) -> int:
        return len(self._queues)

    def has_subscribers(self) -> bool:
        return self.subscriber_count > 0

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


def create_app(
    root: str,
    sse_manager: SSEManager | None = None,
    shutdown_callback: Callable[[], None] | None = None,
) -> Starlette:
    """Create the Starlette web UI application.

    Args:
        root: Path to the pixie artifact root directory.
        sse_manager: Optional SSE manager instance (created if not provided).
        shutdown_callback: Optional callback invoked by the ``/api/shutdown``
            endpoint to request a graceful server shutdown.

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
        elif resolved.suffix in (".md", ".jsonl", ".py"):
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

    async def api_status(request: Request) -> JSONResponse:
        return JSONResponse({"active_clients": sse.subscriber_count})

    async def api_navigate(request: Request) -> JSONResponse:
        """Broadcast a navigate event to all connected SSE clients."""
        tab = request.query_params.get("tab")
        item_id = request.query_params.get("id")
        if not tab:
            return JSONResponse({"error": "tab parameter required"}, status_code=400)
        payload: dict[str, str] = {"tab": tab}
        if item_id:
            payload["id"] = item_id
        await sse.broadcast("navigate", payload)
        return JSONResponse({"ok": True})

    async def api_result(request: Request) -> Response:
        """Serve a test result reconstructed from the per-entry file structure."""
        test_id = request.query_params.get("id", "")
        if not test_id:
            return JSONResponse({"error": "id parameter required"}, status_code=400)

        # Prevent path traversal
        safe_id = Path(test_id).name
        result_dir = artifact_root / "results" / safe_id
        meta_file = result_dir / "meta.json"

        if not meta_file.exists():
            return JSONResponse({"error": "result not found"}, status_code=404)

        meta = json.loads(meta_file.read_text(encoding="utf-8"))

        # Reconstruct datasets from directory structure
        datasets: list[dict[str, object]] = []
        ds_idx = 0
        while True:
            ds_dir = result_dir / f"dataset-{ds_idx}"
            if not ds_dir.is_dir():
                break

            ds_meta_path = ds_dir / "metadata.json"
            ds_meta = (
                json.loads(ds_meta_path.read_text(encoding="utf-8"))
                if ds_meta_path.exists()
                else {}
            )

            entries: list[dict[str, object]] = []
            entry_idx = 0
            while True:
                entry_dir = ds_dir / f"entry-{entry_idx}"
                if not entry_dir.is_dir():
                    break

                # Read config
                config_path = entry_dir / "config.json"
                config = (
                    json.loads(config_path.read_text(encoding="utf-8"))
                    if config_path.exists()
                    else {}
                )

                # Read eval-input (collapse for display)
                eval_input = _read_jsonl_file(entry_dir / "eval-input.jsonl")
                input_val = _collapse_named_items(eval_input)

                # Read eval-output (collapse for display)
                eval_output = _read_jsonl_file(entry_dir / "eval-output.jsonl")
                output_val = _collapse_named_items(eval_output)

                # Read evaluations
                evaluations = _read_jsonl_file(entry_dir / "evaluations.jsonl")

                entry: dict[str, object] = {
                    "input": input_val,
                    "output": output_val,
                    "evaluations": evaluations,
                }
                if config.get("expectation") is not None:
                    entry["expectedOutput"] = config["expectation"]
                if config.get("description") is not None:
                    entry["description"] = config["description"]

                # Entry analysis
                entry_analysis_path = entry_dir / "analysis.md"
                if entry_analysis_path.exists():
                    entry["analysis"] = entry_analysis_path.read_text(encoding="utf-8")

                entries.append(entry)
                entry_idx += 1

            ds_data: dict[str, object] = {
                "dataset": ds_meta.get("dataset", f"dataset-{ds_idx}"),
                "entries": entries,
            }

            # Dataset analysis
            ds_analysis_path = ds_dir / "analysis.md"
            if ds_analysis_path.exists():
                ds_data["analysis"] = ds_analysis_path.read_text(encoding="utf-8")

            datasets.append(ds_data)
            ds_idx += 1

        return JSONResponse({"meta": meta, "datasets": datasets})

    async def api_shutdown(request: Request) -> JSONResponse:
        """Initiate a graceful server shutdown."""
        if shutdown_callback is not None:
            shutdown_callback()
        return JSONResponse({"ok": True})

    routes = [
        Route("/", index),
        Route("/api/manifest", api_manifest),
        Route("/api/file", api_file_content),
        Route("/api/result", api_result),
        Route("/api/events", api_events),
        Route("/api/status", api_status),
        Route("/api/navigate", api_navigate),
        Route("/api/shutdown", api_shutdown, methods=["POST"]),
    ]

    return Starlette(routes=routes)
