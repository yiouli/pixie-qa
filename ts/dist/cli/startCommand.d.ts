/**
 * `pixie-qa start` — launch the web UI for browsing eval artifacts.
 *
 * Usage:
 *   pixie-qa start [root]
 *
 * Ensures the pixie working directory is initialized, then starts a local
 * HTTP server that serves a React web UI for browsing scorecards, datasets,
 * and markdown artifacts. The UI updates live when files change.
 */
/**
 * Initialize the pixie directory (if needed) and launch the web UI server.
 *
 * @param root - Optional explicit artifact root directory.
 * @param tab - Optional tab to pre-select (e.g. "scorecards").
 * @param itemId - Optional item path to pre-select within the tab.
 * @returns Exit code (0 on normal shutdown).
 */
export declare function start(root?: string, tab?: string, itemId?: string): Promise<number>;
//# sourceMappingURL=startCommand.d.ts.map