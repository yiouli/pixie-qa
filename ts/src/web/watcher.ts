/**
 * File watcher for pixie artifact directories.
 *
 * Uses chokidar to monitor the pixie root for artifact changes
 * (markdown, datasets, scorecards) and pushes SSE events to all subscribers.
 */

import { watch, type FSWatcher } from "chokidar";
import fs from "fs";
import path from "path";

import type { SSEManager } from "./app";
import { buildManifest } from "./app";

/** File suffixes we care about. */
const WATCHED_SUFFIXES = new Set([".md", ".json", ".html"]);

/**
 * Return true if the path is a relevant artifact file.
 */
function isArtifact(filePath: string, root: string): boolean {
  const ext = path.extname(filePath);
  if (!WATCHED_SUFFIXES.has(ext)) return false;

  let rel: string;
  try {
    rel = path.relative(root, filePath);
  } catch {
    return false;
  }

  // Reject paths outside root
  if (rel.startsWith("..")) return false;

  const parts = rel.split(path.sep);

  // Top-level .md files
  if (parts.length === 1 && ext === ".md") return true;
  // datasets/*.json
  if (parts.length === 2 && parts[0] === "datasets" && ext === ".json") return true;
  // scorecards/*.html
  if (parts.length === 2 && parts[0] === "scorecards" && ext === ".html") return true;
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
export function watchArtifacts(root: string, sse: SSEManager): FSWatcher {
  const rootPath = path.resolve(root);

  // Ensure watched directories exist
  fs.mkdirSync(rootPath, { recursive: true });
  fs.mkdirSync(path.join(rootPath, "datasets"), { recursive: true });
  fs.mkdirSync(path.join(rootPath, "scorecards"), { recursive: true });
  fs.mkdirSync(path.join(rootPath, "results"), { recursive: true });

  const watcher = watch(rootPath, {
    ignoreInitial: true,
    persistent: true,
  });

  const handleChange = (changeType: string, filePath: string): void => {
    if (!isArtifact(filePath, rootPath)) return;

    const relPath = path.relative(rootPath, filePath);
    const change = { type: changeType, path: relPath };
    sse.broadcast("file_change", [change]);
    const manifest = buildManifest(rootPath);
    sse.broadcast("manifest", manifest);
  };

  watcher.on("add", (filePath) => handleChange("added", filePath));
  watcher.on("change", (filePath) => handleChange("modified", filePath));
  watcher.on("unlink", (filePath) => handleChange("deleted", filePath));

  return watcher;
}
