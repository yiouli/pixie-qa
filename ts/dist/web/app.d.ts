/**
 * Express application for the pixie web UI.
 *
 * Serves the single-page React app and provides API endpoints for:
 * - listing / reading artifacts (markdown, datasets, scorecards)
 * - SSE stream for live file-change notifications
 */
import express from "express";
import type { Response } from "express";
/** Build a full manifest of all artifacts. */
export declare function buildManifest(root: string): Record<string, unknown>;
/**
 * Manages Server-Sent Events connections and broadcasts.
 */
export declare class SSEManager {
    private _responses;
    subscribe(res: Response): void;
    get subscriberCount(): number;
    hasSubscribers(): boolean;
    broadcast(eventType: string, data: unknown): void;
}
/**
 * Create the Express web UI application.
 *
 * @param root - Path to the pixie artifact root directory.
 * @param sseManager - Optional SSE manager instance (created if not provided).
 * @returns A configured Express application.
 */
export declare function createApp(root: string, sseManager?: SSEManager): express.Express;
//# sourceMappingURL=app.d.ts.map