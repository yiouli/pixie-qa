"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.start = start;
const initCommand_1 = require("./initCommand");
const config_1 = require("../config");
const server_1 = require("../web/server");
/**
 * Initialize the pixie directory (if needed) and launch the web UI server.
 *
 * @param root - Optional explicit artifact root directory.
 * @param tab - Optional tab to pre-select (e.g. "scorecards").
 * @param itemId - Optional item path to pre-select within the tab.
 * @returns Exit code (0 on normal shutdown).
 */
async function start(root, tab, itemId) {
    const config = (0, config_1.getConfig)();
    const artifactRoot = root ?? config.root;
    (0, initCommand_1.initPixieDir)(artifactRoot);
    await (0, server_1.runServer)(artifactRoot, { tab, itemId });
    return 0;
}
//# sourceMappingURL=startCommand.js.map