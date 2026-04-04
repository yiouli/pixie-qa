/**
 * Express application for the pixie web UI.
 *
 * Serves the single-page React app and provides API endpoints for:
 * - listing / reading artifacts (markdown, datasets, scorecards)
 * - SSE stream for live file-change notifications
 */

import express from "express";
import type { Request, Response } from "express";
import fs from "fs";
import path from "path";

// ── Helpers ──────────────────────────────────────────────────────────────────

function resolveArtifactRoot(root: string): string {
  return path.resolve(root);
}

function listMdFiles(root: string): Array<{ name: string; path: string }> {
  const files: Array<{ name: string; path: string }> = [];
  if (!fs.existsSync(root)) return files;
  const entries = fs.readdirSync(root);
  for (const entry of entries.sort()) {
    if (entry.endsWith(".md")) {
      files.push({ name: entry, path: entry });
    }
  }
  return files;
}

function listDatasets(root: string): Array<{ name: string; path: string }> {
  const dsDir = path.join(root, "datasets");
  const files: Array<{ name: string; path: string }> = [];
  if (!fs.existsSync(dsDir)) return files;
  const entries = fs.readdirSync(dsDir);
  for (const entry of entries.sort()) {
    if (entry.endsWith(".json")) {
      const stem = path.basename(entry, ".json");
      files.push({ name: stem, path: `datasets/${entry}` });
    }
  }
  return files;
}

function listScorecards(root: string): Array<{ name: string; path: string }> {
  const scDir = path.join(root, "scorecards");
  const files: Array<{ name: string; path: string }> = [];
  if (!fs.existsSync(scDir)) return files;
  const entries = fs.readdirSync(scDir);
  for (const entry of entries.sort().reverse()) {
    if (entry.endsWith(".html")) {
      const stem = path.basename(entry, ".html");
      files.push({ name: stem, path: `scorecards/${entry}` });
    }
  }
  return files;
}

function listResults(root: string): Array<{ name: string; path: string }> {
  const resultsDir = path.join(root, "results");
  const dirs: Array<{ name: string; path: string }> = [];
  if (!fs.existsSync(resultsDir)) return dirs;
  const entries = fs.readdirSync(resultsDir);
  for (const entry of entries.sort().reverse()) {
    const dirPath = path.join(resultsDir, entry);
    const stat = fs.statSync(dirPath, { throwIfNoEntry: false });
    if (stat?.isDirectory() && fs.existsSync(path.join(dirPath, "result.json"))) {
      dirs.push({ name: entry, path: `results/${entry}` });
    }
  }
  return dirs;
}

/** Build a full manifest of all artifacts. */
export function buildManifest(root: string): Record<string, unknown> {
  return {
    markdownFiles: listMdFiles(root),
    datasets: listDatasets(root),
    scorecards: listScorecards(root),
    results: listResults(root),
  };
}

// ── SSEManager ───────────────────────────────────────────────────────────────

/**
 * Manages Server-Sent Events connections and broadcasts.
 */
export class SSEManager {
  private _responses: Response[] = [];

  subscribe(res: Response): void {
    this._responses.push(res);
    res.on("close", () => {
      this._responses = this._responses.filter((r) => r !== res);
    });
  }

  get subscriberCount(): number {
    return this._responses.length;
  }

  hasSubscribers(): boolean {
    return this._responses.length > 0;
  }

  broadcast(eventType: string, data: unknown): void {
    const payload = `event: ${eventType}\ndata: ${JSON.stringify(data)}\n\n`;
    const dead: Response[] = [];
    for (const res of this._responses) {
      try {
        res.write(payload);
      } catch {
        dead.push(res);
      }
    }
    if (dead.length > 0) {
      this._responses = this._responses.filter((r) => !dead.includes(r));
    }
  }
}

// ── App factory ──────────────────────────────────────────────────────────────

function loadWebuiHtml(): string {
  const assetsDir = path.join(__dirname, "..", "assets");
  const webuiFile = path.join(assetsDir, "webui.html");
  return fs.readFileSync(webuiFile, "utf-8");
}

/**
 * Create the Express web UI application.
 *
 * @param root - Path to the pixie artifact root directory.
 * @param sseManager - Optional SSE manager instance (created if not provided).
 * @returns A configured Express application.
 */
export function createApp(
  root: string,
  sseManager?: SSEManager
): express.Express {
  const artifactRoot = resolveArtifactRoot(root);
  const sse = sseManager ?? new SSEManager();
  const app = express();

  // GET /
  app.get("/", (_req: Request, res: Response) => {
    try {
      const html = loadWebuiHtml();
      res.type("html").send(html);
    } catch {
      res
        .status(500)
        .type("html")
        .send("<h1>Web UI not built</h1><p>Run <code>cd frontend && npm run build</code></p>");
    }
  });

  // GET /api/manifest
  app.get("/api/manifest", (_req: Request, res: Response) => {
    const manifest = buildManifest(artifactRoot);
    res.json(manifest);
  });

  // GET /api/file?path=...
  app.get("/api/file", (req: Request, res: Response) => {
    const filePath = req.query["path"] as string | undefined;
    if (!filePath) {
      res.status(400).json({ error: "path parameter required" });
      return;
    }

    // Prevent path traversal
    const resolved = path.resolve(artifactRoot, filePath);
    if (!resolved.startsWith(artifactRoot)) {
      res.status(403).json({ error: "invalid path" });
      return;
    }

    if (!fs.existsSync(resolved)) {
      res.status(404).json({ error: "file not found" });
      return;
    }

    const ext = path.extname(resolved);
    const content = fs.readFileSync(resolved, "utf-8");

    if (ext === ".json") {
      res.json(JSON.parse(content));
    } else if (ext === ".html") {
      res.type("html").send(content);
    } else if (ext === ".md") {
      res.json({ content });
    } else {
      res.status(400).json({ error: "unsupported file type" });
    }
  });

  // GET /api/result?id=...
  app.get("/api/result", (req: Request, res: Response) => {
    const testId = req.query["id"] as string | undefined;
    if (!testId) {
      res.status(400).json({ error: "id parameter required" });
      return;
    }

    // Prevent path traversal
    const safeId = path.basename(testId);
    const resultDir = path.join(artifactRoot, "results", safeId);
    const resultFile = path.join(resultDir, "result.json");

    if (!fs.existsSync(resultFile)) {
      res.status(404).json({ error: "result not found" });
      return;
    }

    const content = fs.readFileSync(resultFile, "utf-8");
    const data = JSON.parse(content);

    // Merge analysis markdown into dataset objects
    const datasets = data.datasets ?? [];
    for (let i = 0; i < datasets.length; i++) {
      const analysisPath = path.join(resultDir, `dataset-${i}.md`);
      if (fs.existsSync(analysisPath)) {
        datasets[i].analysis = fs.readFileSync(analysisPath, "utf-8");
      }
    }

    res.json(data);
  });

  // GET /api/events (SSE)
  app.get("/api/events", (_req: Request, res: Response) => {
    res.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    });

    // Send initial manifest
    const manifest = buildManifest(artifactRoot);
    res.write(`event: manifest\ndata: ${JSON.stringify(manifest)}\n\n`);

    sse.subscribe(res);
  });

  // GET /api/status
  app.get("/api/status", (_req: Request, res: Response) => {
    res.json({ active_clients: sse.subscriberCount });
  });

  // GET /api/navigate?tab=...&id=...
  app.get("/api/navigate", (req: Request, res: Response) => {
    const tab = req.query["tab"] as string | undefined;
    const itemId = req.query["id"] as string | undefined;
    if (!tab) {
      res.status(400).json({ error: "tab parameter required" });
      return;
    }
    const payload: Record<string, string> = { tab };
    if (itemId) {
      payload["id"] = itemId;
    }
    sse.broadcast("navigate", payload);
    res.json({ ok: true });
  });

  return app;
}
