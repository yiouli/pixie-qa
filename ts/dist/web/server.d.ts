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
/**
 * Build the web UI URL with optional query parameters.
 */
export declare function buildUrl(host?: string, port?: number, tab?: string, itemId?: string): string;
/** Status of the pixie web server for a given root. */
export interface ServerStatus {
    running: boolean;
    port: number | null;
    activeClients: number;
}
/**
 * Return the status of the pixie web server for `root`.
 */
export declare function getServerStatus(root: string, host?: string): Promise<ServerStatus>;
export interface RunServerOptions {
    host?: string;
    port?: number;
    openBrowser?: boolean;
    tab?: string;
    itemId?: string;
}
/**
 * Start the pixie web UI server.
 *
 * Writes a `server.lock` to `root` on startup and removes it on shutdown.
 */
export declare function runServer(root: string, opts?: RunServerOptions): Promise<void>;
/**
 * Open the web UI, starting the server in the background if needed.
 *
 * Checks the `server.lock` file to discover whether a server is already
 * running. If it is, opens the browser or sends a navigate event.
 * Otherwise starts the server.
 */
export declare function openWebui(root: string, opts?: {
    host?: string;
    port?: number;
    tab?: string;
    itemId?: string;
}): Promise<void>;
//# sourceMappingURL=server.d.ts.map