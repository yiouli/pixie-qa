# Pixie Frontend

React frontend for Pixie's live dashboard (`pixie start`).

The production build now targets the Web UI only. Legacy scorecard code remains in the repo for viewing historical standalone scorecard artifacts, but it is no longer part of the default build flow.

## Quick Start

```bash
# Install dependencies
npm install

# Start Web UI dev server
npm run dev

# Build Web UI for production (output: ../pixie/assets/webui.html)
npm run build

# Preview built output
npm run preview
```

## Stack

- React 19 + TypeScript 5.7
- Vite 6
- vite-plugin-singlefile (inlines JS/CSS into a single HTML file)

## Project Structure

```text
src/
├── webui-main.tsx        # Web UI entry point
├── webui/                # Web UI app
│   ├── WebUIApp.tsx      # Main app shell and tab routing
│   ├── types.ts          # Manifest and result types
│   ├── useSSE.ts         # SSE connection state
│   ├── markdown.ts       # Minimal markdown renderer
│   ├── webui.css         # Web UI styles
│   └── components/
│       ├── ResultsPanel.tsx
│       ├── ScorecardsPanel.tsx   # legacy scorecard viewer
│       ├── DatasetsPanel.tsx
│       ├── MarkdownPanel.tsx
│       ├── SidebarList.tsx
│       └── TabBar.tsx
├── main.tsx              # Legacy scorecard entry (not default build)
├── App.tsx               # Legacy scorecard app root
└── components/           # Shared/legacy scorecard components
```

## Build Targets

Build selection uses `VITE_BUILD_TARGET`:

- `webui` (default) -> `webui.html` -> `../pixie/assets/webui.html`
- `scorecard` (legacy/manual only) -> `index.html` -> `../pixie/assets/index.html`

`npm run build` compiles only the `webui` target.

## Runtime Behavior

For `pixie start`:

1. Python serves `webui.html` and API endpoints from a Starlette app.
2. The CLI waits until the detached server responds before reporting success and opening the browser, so fresh `server.lock` files written during startup are not mistaken for stale failures.
3. The frontend fetches `/api/manifest` to list available artifacts.
4. The frontend subscribes to `/api/events` (SSE) for live updates.
5. Results, datasets, markdown files, and legacy scorecards are rendered in dedicated panels.

## Legacy Notes

- Historical scorecards remain viewable in the Web UI Scorecards tab.
- If you explicitly need to build the legacy scorecard artifact for debugging, run:

```bash
VITE_BUILD_TARGET=scorecard vite build
```
