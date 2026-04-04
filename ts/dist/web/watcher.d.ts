/**
 * File watcher for pixie artifact directories.
 *
 * Uses chokidar to monitor the pixie root for artifact changes
 * (markdown, datasets, scorecards) and pushes SSE events to all subscribers.
 */
import { type FSWatcher } from "chokidar";
import type { SSEManager } from "./app";
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
export declare function watchArtifacts(root: string, sse: SSEManager): FSWatcher;
//# sourceMappingURL=watcher.d.ts.map