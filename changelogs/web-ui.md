# Changelog: Web UI (`pixie start`) and scorecard viewing

## What Changed

Added a local web UI that renders eval-driven-dev artifacts (markdown files, datasets, scorecards) with live updates via Server-Sent Events.

Changed `pixie test` to open the web UI (instead of the raw scorecard HTML file) after generating a scorecard. If the web UI server is not running, it starts one in the background.

Changed `pixie init` to immediately launch the web UI after scaffolding so it behaves like `pixie init && pixie start`.

### New CLI command

- `pixie start [root]` — starts a local HTTP server and opens the web UI in the default browser. If the default port (7118) is already in use, assumes a server is running and opens the browser only.

### `pixie init` chaining behavior

- `pixie init` now scaffolds directories and then invokes `pixie start` behavior automatically
- The init step remains idempotent; existing directories/files are preserved
- The follow-up web UI launch uses the same root argument resolution as `pixie start`

### Scorecard viewing after `pixie test`

- `pixie test` no longer opens the raw scorecard HTML file in the browser
- Instead, it opens the web UI with `?tab=scorecards&id=<scorecard_path>` to show the just-generated scorecard
- If the server is already running, it just opens the browser to it
- If the server is not running, it starts one on a background daemon thread and opens the browser
- `--no-open` flag still suppresses all browser opening
- The web UI also supports `?tab=datasets&id=<path>` for deep-linking to datasets

### Backend (Python)

- **pixie/web/app.py** — Starlette application with API routes:
  - `GET /` — serves the compiled webui.html
  - `GET /api/manifest` — returns JSON listing all markdown files, datasets, and scorecards
  - `GET /api/file?path=...` — serves individual artifact files (md, json, html) with path traversal protection
  - `GET /api/events` — SSE endpoint for live update notifications
- **pixie/web/watcher.py** — Watches the artifact root directory using `watchfiles.awatch` and broadcasts `file_change` and `manifest` events via SSE when artifacts are added, modified, or removed.
- **pixie/web/server.py** — Uvicorn runner with `run_server()` (blocking), `open_webui()` (non-blocking, starts daemon thread if needed), and `build_url()` (constructs URL with query params).
- **pixie/cli/start_command.py** — CLI command handler for `pixie start`, accepts optional `tab`/`item_id` for deep-linking.

### Frontend (React + TypeScript)

- **frontend/src/webui/** — New web UI application:
  - `WebUIApp.tsx` — Main app with SSE-driven state, dynamic tabs (Scorecards, Datasets, one per .md file)
  - `useSSE.ts` — React hook for EventSource connection to `/api/events`
  - `markdown.ts` — Zero-dependency markdown-to-HTML converter
  - `webui.css` — Full stylesheet extending the Ink & Signal design system
  - `components/TabBar.tsx` — Tab navigation
  - `components/SidebarList.tsx` — Sidebar list for item selection
  - `components/ScorecardsPanel.tsx` — Split panel with sidebar + iframe viewer
  - `components/DatasetsPanel.tsx` — Split panel with sidebar + table viewer
  - `components/MarkdownPanel.tsx` — Markdown file renderer
- **frontend/webui.html** — HTML template for the webui build target
- **frontend/src/webui-main.tsx** — Entry point for the webui React app

### Build system

- Vite config updated for dual-target builds via `VITE_BUILD_TARGET` env var:
  - `scorecard` (default) → `pixie/assets/index.html`
  - `webui` → `pixie/assets/webui.html`
- `npm run build` now builds both targets sequentially

### Scorecard iframe integration

- `App.tsx` detects iframe embedding (`window.self !== window.top`) and hides the BrandHeader when embedded in the web UI.

## Files Affected

### New files

- `pixie/web/__init__.py`
- `pixie/web/app.py`
- `pixie/web/watcher.py`
- `pixie/web/server.py`
- `pixie/cli/start_command.py`
- `frontend/src/webui-main.tsx`
- `frontend/webui.html`
- `frontend/src/webui/WebUIApp.tsx`
- `frontend/src/webui/types.ts`
- `frontend/src/webui/useSSE.ts`
- `frontend/src/webui/markdown.ts`
- `frontend/src/webui/webui.css`
- `frontend/src/webui/components/TabBar.tsx`
- `frontend/src/webui/components/SidebarList.tsx`
- `frontend/src/webui/components/ScorecardsPanel.tsx`
- `frontend/src/webui/components/DatasetsPanel.tsx`
- `frontend/src/webui/components/MarkdownPanel.tsx`
- `tests/pixie/web/__init__.py`
- `tests/pixie/web/test_app.py`
- `tests/pixie/web/test_watcher.py`

### Modified files

- `pixie/cli/main.py` — added `start` subcommand and made `init` invoke `start` after scaffolding
- `pixie/cli/test_command.py` — replaced `webbrowser.open(file_uri)` with `open_webui()` call to show scorecard in web UI
- `frontend/vite.config.ts` — dual-target build
- `frontend/package.json` — new build scripts
- `frontend/src/App.tsx` — iframe header hiding
- `pyproject.toml` — added starlette, uvicorn, watchfiles dependencies; webui.html force-include

## Migration Notes

- Three new runtime dependencies: `starlette>=0.46`, `uvicorn>=0.34`, `watchfiles>=1.0`
- Run `uv sync` to install new dependencies
- Run `npm run build` in `frontend/` to rebuild both HTML assets after frontend changes
