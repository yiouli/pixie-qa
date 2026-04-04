"use strict";
/**
 * Express application for the pixie web UI.
 *
 * Serves the single-page React app and provides API endpoints for:
 * - listing / reading artifacts (markdown, datasets, scorecards)
 * - SSE stream for live file-change notifications
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.SSEManager = void 0;
exports.buildManifest = buildManifest;
exports.createApp = createApp;
const express_1 = __importDefault(require("express"));
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
// ── Helpers ──────────────────────────────────────────────────────────────────
function resolveArtifactRoot(root) {
    return path_1.default.resolve(root);
}
function listMdFiles(root) {
    const files = [];
    if (!fs_1.default.existsSync(root))
        return files;
    const entries = fs_1.default.readdirSync(root);
    for (const entry of entries.sort()) {
        if (entry.endsWith(".md")) {
            files.push({ name: entry, path: entry });
        }
    }
    return files;
}
function listDatasets(root) {
    const dsDir = path_1.default.join(root, "datasets");
    const files = [];
    if (!fs_1.default.existsSync(dsDir))
        return files;
    const entries = fs_1.default.readdirSync(dsDir);
    for (const entry of entries.sort()) {
        if (entry.endsWith(".json")) {
            const stem = path_1.default.basename(entry, ".json");
            files.push({ name: stem, path: `datasets/${entry}` });
        }
    }
    return files;
}
function listScorecards(root) {
    const scDir = path_1.default.join(root, "scorecards");
    const files = [];
    if (!fs_1.default.existsSync(scDir))
        return files;
    const entries = fs_1.default.readdirSync(scDir);
    for (const entry of entries.sort().reverse()) {
        if (entry.endsWith(".html")) {
            const stem = path_1.default.basename(entry, ".html");
            files.push({ name: stem, path: `scorecards/${entry}` });
        }
    }
    return files;
}
function listResults(root) {
    const resultsDir = path_1.default.join(root, "results");
    const dirs = [];
    if (!fs_1.default.existsSync(resultsDir))
        return dirs;
    const entries = fs_1.default.readdirSync(resultsDir);
    for (const entry of entries.sort().reverse()) {
        const dirPath = path_1.default.join(resultsDir, entry);
        const stat = fs_1.default.statSync(dirPath, { throwIfNoEntry: false });
        if (stat?.isDirectory() && fs_1.default.existsSync(path_1.default.join(dirPath, "result.json"))) {
            dirs.push({ name: entry, path: `results/${entry}` });
        }
    }
    return dirs;
}
/** Build a full manifest of all artifacts. */
function buildManifest(root) {
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
class SSEManager {
    _responses = [];
    subscribe(res) {
        this._responses.push(res);
        res.on("close", () => {
            this._responses = this._responses.filter((r) => r !== res);
        });
    }
    get subscriberCount() {
        return this._responses.length;
    }
    hasSubscribers() {
        return this._responses.length > 0;
    }
    broadcast(eventType, data) {
        const payload = `event: ${eventType}\ndata: ${JSON.stringify(data)}\n\n`;
        const dead = [];
        for (const res of this._responses) {
            try {
                res.write(payload);
            }
            catch {
                dead.push(res);
            }
        }
        if (dead.length > 0) {
            this._responses = this._responses.filter((r) => !dead.includes(r));
        }
    }
}
exports.SSEManager = SSEManager;
// ── App factory ──────────────────────────────────────────────────────────────
function loadWebuiHtml() {
    const assetsDir = path_1.default.join(__dirname, "..", "assets");
    const webuiFile = path_1.default.join(assetsDir, "webui.html");
    return fs_1.default.readFileSync(webuiFile, "utf-8");
}
/**
 * Create the Express web UI application.
 *
 * @param root - Path to the pixie artifact root directory.
 * @param sseManager - Optional SSE manager instance (created if not provided).
 * @returns A configured Express application.
 */
function createApp(root, sseManager) {
    const artifactRoot = resolveArtifactRoot(root);
    const sse = sseManager ?? new SSEManager();
    const app = (0, express_1.default)();
    // GET /
    app.get("/", (_req, res) => {
        try {
            const html = loadWebuiHtml();
            res.type("html").send(html);
        }
        catch {
            res
                .status(500)
                .type("html")
                .send("<h1>Web UI not built</h1><p>Run <code>cd frontend && npm run build</code></p>");
        }
    });
    // GET /api/manifest
    app.get("/api/manifest", (_req, res) => {
        const manifest = buildManifest(artifactRoot);
        res.json(manifest);
    });
    // GET /api/file?path=...
    app.get("/api/file", (req, res) => {
        const filePath = req.query["path"];
        if (!filePath) {
            res.status(400).json({ error: "path parameter required" });
            return;
        }
        // Prevent path traversal
        const resolved = path_1.default.resolve(artifactRoot, filePath);
        if (!resolved.startsWith(artifactRoot)) {
            res.status(403).json({ error: "invalid path" });
            return;
        }
        if (!fs_1.default.existsSync(resolved)) {
            res.status(404).json({ error: "file not found" });
            return;
        }
        const ext = path_1.default.extname(resolved);
        const content = fs_1.default.readFileSync(resolved, "utf-8");
        if (ext === ".json") {
            res.json(JSON.parse(content));
        }
        else if (ext === ".html") {
            res.type("html").send(content);
        }
        else if (ext === ".md") {
            res.json({ content });
        }
        else {
            res.status(400).json({ error: "unsupported file type" });
        }
    });
    // GET /api/result?id=...
    app.get("/api/result", (req, res) => {
        const testId = req.query["id"];
        if (!testId) {
            res.status(400).json({ error: "id parameter required" });
            return;
        }
        // Prevent path traversal
        const safeId = path_1.default.basename(testId);
        const resultDir = path_1.default.join(artifactRoot, "results", safeId);
        const resultFile = path_1.default.join(resultDir, "result.json");
        if (!fs_1.default.existsSync(resultFile)) {
            res.status(404).json({ error: "result not found" });
            return;
        }
        const content = fs_1.default.readFileSync(resultFile, "utf-8");
        const data = JSON.parse(content);
        // Merge analysis markdown into dataset objects
        const datasets = data.datasets ?? [];
        for (let i = 0; i < datasets.length; i++) {
            const analysisPath = path_1.default.join(resultDir, `dataset-${i}.md`);
            if (fs_1.default.existsSync(analysisPath)) {
                datasets[i].analysis = fs_1.default.readFileSync(analysisPath, "utf-8");
            }
        }
        res.json(data);
    });
    // GET /api/events (SSE)
    app.get("/api/events", (_req, res) => {
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
    app.get("/api/status", (_req, res) => {
        res.json({ active_clients: sse.subscriberCount });
    });
    // GET /api/navigate?tab=...&id=...
    app.get("/api/navigate", (req, res) => {
        const tab = req.query["tab"];
        const itemId = req.query["id"];
        if (!tab) {
            res.status(400).json({ error: "tab parameter required" });
            return;
        }
        const payload = { tab };
        if (itemId) {
            payload["id"] = itemId;
        }
        sse.broadcast("navigate", payload);
        res.json({ ok: true });
    });
    return app;
}
//# sourceMappingURL=app.js.map