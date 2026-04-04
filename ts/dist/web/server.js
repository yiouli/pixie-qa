"use strict";
/**
 * Server runner for the pixie web UI.
 *
 * Starts the Express app with Node http server, launches the file watcher,
 * and optionally opens the browser.
 *
 * A `server.lock` file is written to the pixie artifact root on startup
 * (containing the port number) and removed on shutdown. Other processes
 * (e.g. `openWebui` or `pixie-qa test`) read this file to discover whether
 * the server is already running and on which port.
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildUrl = buildUrl;
exports.getServerStatus = getServerStatus;
exports.runServer = runServer;
exports.openWebui = openWebui;
const fs_1 = __importDefault(require("fs"));
const http_1 = __importDefault(require("http"));
const net_1 = __importDefault(require("net"));
const path_1 = __importDefault(require("path"));
const child_process_1 = require("child_process");
const app_1 = require("./app");
const watcher_1 = require("./watcher");
const DEFAULT_HOST = "127.0.0.1";
const DEFAULT_PORT = 7118;
const LOCK_FILENAME = "server.lock";
/**
 * Open a URL in the default browser using platform-native commands.
 */
function openInBrowser(url) {
    const platform = process.platform;
    let cmd;
    if (platform === "darwin") {
        cmd = `open "${url}"`;
    }
    else if (platform === "win32") {
        cmd = `start "" "${url}"`;
    }
    else {
        cmd = `xdg-open "${url}"`;
    }
    (0, child_process_1.exec)(cmd, (err) => {
        if (err) {
            console.log(`Open ${url} in your browser`);
        }
    });
}
/**
 * Build the web UI URL with optional query parameters.
 */
function buildUrl(host = DEFAULT_HOST, port = DEFAULT_PORT, tab, itemId) {
    let url = `http://${host}:${port}`;
    const params = [];
    if (tab)
        params.push(`tab=${tab}`);
    if (itemId)
        params.push(`id=${encodeURIComponent(itemId)}`);
    if (params.length > 0) {
        url += "?" + params.join("&");
    }
    return url;
}
function findOpenPort(host, startPort) {
    return new Promise((resolve) => {
        const tryPort = (port) => {
            if (port >= startPort + 100) {
                resolve(startPort);
                return;
            }
            const server = net_1.default.createServer();
            server.once("error", () => tryPort(port + 1));
            server.once("listening", () => {
                server.close(() => resolve(port));
            });
            server.listen(port, host);
        };
        tryPort(startPort);
    });
}
function isPortInUse(host, port) {
    return new Promise((resolve) => {
        const server = net_1.default.createServer();
        server.once("error", () => resolve(true));
        server.once("listening", () => {
            server.close(() => resolve(false));
        });
        server.listen(port, host);
    });
}
function lockPath(root) {
    return path_1.default.join(path_1.default.resolve(root), LOCK_FILENAME);
}
function writeLock(root, port) {
    const lp = lockPath(root);
    fs_1.default.mkdirSync(path_1.default.dirname(lp), { recursive: true });
    fs_1.default.writeFileSync(lp, String(port));
}
function removeLock(root) {
    try {
        fs_1.default.unlinkSync(lockPath(root));
    }
    catch {
        // ignore if not found
    }
}
function readLock(root) {
    try {
        const content = fs_1.default.readFileSync(lockPath(root), "utf-8").trim();
        const port = parseInt(content, 10);
        return isNaN(port) ? null : port;
    }
    catch {
        return null;
    }
}
/**
 * Probe the server's `/api/status` endpoint.
 * Returns the active client count if the server responds, otherwise null.
 */
async function probeServer(host, port) {
    return new Promise((resolve) => {
        const req = http_1.default.get(`http://${host}:${port}/api/status`, { timeout: 2000 }, (res) => {
            let body = "";
            res.on("data", (chunk) => (body += chunk.toString()));
            res.on("end", () => {
                try {
                    const data = JSON.parse(body);
                    resolve(typeof data.active_clients === "number" ? data.active_clients : 0);
                }
                catch {
                    resolve(null);
                }
            });
        });
        req.on("error", () => resolve(null));
        req.on("timeout", () => {
            req.destroy();
            resolve(null);
        });
    });
}
/**
 * Ask the running server to broadcast a `navigate` SSE event.
 */
async function sendNavigate(host, port, tab, itemId) {
    const params = [];
    if (tab)
        params.push(`tab=${tab}`);
    if (itemId)
        params.push(`id=${encodeURIComponent(itemId)}`);
    if (params.length === 0)
        return false;
    return new Promise((resolve) => {
        const req = http_1.default.get(`http://${host}:${port}/api/navigate?${params.join("&")}`, { timeout: 2000 }, (res) => {
            res.resume();
            resolve(res.statusCode === 200);
        });
        req.on("error", () => resolve(false));
        req.on("timeout", () => {
            req.destroy();
            resolve(false);
        });
    });
}
async function isServerRunning(root, host = DEFAULT_HOST) {
    const port = readLock(root);
    if (port === null)
        return null;
    const active = await probeServer(host, port);
    if (active !== null)
        return port;
    // Stale lock
    removeLock(root);
    return null;
}
/**
 * Return the status of the pixie web server for `root`.
 */
async function getServerStatus(root, host = DEFAULT_HOST) {
    const port = readLock(root);
    if (port === null) {
        return { running: false, port: null, activeClients: 0 };
    }
    const activeClients = await probeServer(host, port);
    if (activeClients === null) {
        removeLock(root);
        return { running: false, port: null, activeClients: 0 };
    }
    return { running: true, port, activeClients };
}
/**
 * Start the pixie web UI server.
 *
 * Writes a `server.lock` to `root` on startup and removes it on shutdown.
 */
async function runServer(root, opts) {
    const host = opts?.host ?? DEFAULT_HOST;
    let port = opts?.port ?? DEFAULT_PORT;
    const openBrowser = opts?.openBrowser ?? true;
    const tab = opts?.tab;
    const itemId = opts?.itemId;
    // Check if a server is already running for this root
    const runningPort = await isServerRunning(root, host);
    if (runningPort !== null) {
        console.log(`Server already running on port ${runningPort}`);
        if (openBrowser) {
            const active = await probeServer(host, runningPort);
            if (active && active > 0) {
                await sendNavigate(host, runningPort, tab, itemId);
            }
            else {
                const url = buildUrl(host, runningPort, tab, itemId);
                openInBrowser(url);
            }
        }
        return;
    }
    // If the default port is taken, find another
    if (await isPortInUse(host, port)) {
        port = await findOpenPort(host, port + 1);
    }
    const sseManager = new app_1.SSEManager();
    const app = (0, app_1.createApp)(root, sseManager);
    const server = http_1.default.createServer(app);
    writeLock(root, port);
    // Clean up on process exit
    const cleanup = () => {
        removeLock(root);
    };
    process.on("SIGINT", () => {
        cleanup();
        server.close();
        process.exit(0);
    });
    process.on("SIGTERM", () => {
        cleanup();
        server.close();
        process.exit(0);
    });
    // Start file watcher
    const watcher = (0, watcher_1.watchArtifacts)(root, sseManager);
    return new Promise((resolve) => {
        server.listen(port, host, () => {
            console.log(`Pixie web UI running at http://${host}:${port}`);
            if (openBrowser) {
                const url = buildUrl(host, port, tab, itemId);
                openInBrowser(url);
            }
        });
        server.on("close", () => {
            cleanup();
            watcher.close();
            resolve();
        });
    });
}
/**
 * Open the web UI, starting the server in the background if needed.
 *
 * Checks the `server.lock` file to discover whether a server is already
 * running. If it is, opens the browser or sends a navigate event.
 * Otherwise starts the server.
 */
async function openWebui(root, opts) {
    const host = opts?.host ?? DEFAULT_HOST;
    const port = opts?.port ?? DEFAULT_PORT;
    const tab = opts?.tab;
    const itemId = opts?.itemId;
    const runningPort = await isServerRunning(root, host);
    if (runningPort !== null) {
        const active = await probeServer(host, runningPort);
        if (active && active > 0) {
            await sendNavigate(host, runningPort, tab, itemId);
        }
        else {
            const url = buildUrl(host, runningPort, tab, itemId);
            openInBrowser(url);
        }
        return;
    }
    // Start the server (non-blocking in the background via runServer)
    void runServer(root, {
        host,
        port,
        openBrowser: true,
        tab,
        itemId,
    });
}
//# sourceMappingURL=server.js.map