"use strict";
/**
 * File watcher for pixie artifact directories.
 *
 * Uses chokidar to monitor the pixie root for artifact changes
 * (markdown, datasets, scorecards) and pushes SSE events to all subscribers.
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.watchArtifacts = watchArtifacts;
const chokidar_1 = require("chokidar");
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const app_1 = require("./app");
/** File suffixes we care about. */
const WATCHED_SUFFIXES = new Set([".md", ".json", ".html"]);
/**
 * Return true if the path is a relevant artifact file.
 */
function isArtifact(filePath, root) {
    const ext = path_1.default.extname(filePath);
    if (!WATCHED_SUFFIXES.has(ext))
        return false;
    let rel;
    try {
        rel = path_1.default.relative(root, filePath);
    }
    catch {
        return false;
    }
    // Reject paths outside root
    if (rel.startsWith(".."))
        return false;
    const parts = rel.split(path_1.default.sep);
    // Top-level .md files
    if (parts.length === 1 && ext === ".md")
        return true;
    // datasets/*.json
    if (parts.length === 2 && parts[0] === "datasets" && ext === ".json")
        return true;
    // scorecards/*.html
    if (parts.length === 2 && parts[0] === "scorecards" && ext === ".html")
        return true;
    // results/<test_id>/result.json or results/<test_id>/dataset-*.md
    if (parts.length === 3 && parts[0] === "results") {
        return ext === ".json" || ext === ".md";
    }
    return false;
}
/**
 * Watch the artifact root for changes and broadcast SSE events.
 *
 * Watches the root directory for file additions, modifications, and
 * deletions. On any relevant change it broadcasts `file_change` and
 * `manifest` SSE events.
 *
 * @param root - Path to the pixie artifact root directory.
 * @param sse - SSE manager to broadcast events through.
 * @returns The chokidar watcher instance (call `.close()` to stop).
 */
function watchArtifacts(root, sse) {
    const rootPath = path_1.default.resolve(root);
    // Ensure watched directories exist
    fs_1.default.mkdirSync(rootPath, { recursive: true });
    fs_1.default.mkdirSync(path_1.default.join(rootPath, "datasets"), { recursive: true });
    fs_1.default.mkdirSync(path_1.default.join(rootPath, "scorecards"), { recursive: true });
    fs_1.default.mkdirSync(path_1.default.join(rootPath, "results"), { recursive: true });
    const watcher = (0, chokidar_1.watch)(rootPath, {
        ignoreInitial: true,
        persistent: true,
    });
    const handleChange = (changeType, filePath) => {
        if (!isArtifact(filePath, rootPath))
            return;
        const relPath = path_1.default.relative(rootPath, filePath);
        const change = { type: changeType, path: relPath };
        sse.broadcast("file_change", [change]);
        const manifest = (0, app_1.buildManifest)(rootPath);
        sse.broadcast("manifest", manifest);
    };
    watcher.on("add", (filePath) => handleChange("added", filePath));
    watcher.on("change", (filePath) => handleChange("modified", filePath));
    watcher.on("unlink", (filePath) => handleChange("deleted", filePath));
    return watcher;
}
//# sourceMappingURL=watcher.js.map