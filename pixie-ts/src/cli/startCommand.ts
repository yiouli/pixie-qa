/**
 * pixie start — launch the web UI for browsing eval artifacts.
 */

import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { getConfig } from "../config.js";
import { initPixieDir } from "./initCommand.js";

const DEFAULT_PORT = 7118;

export function start(root?: string | null): number {
  const config = getConfig();
  const targetRoot = root ?? config.root;
  initPixieDir(targetRoot);

  const absRoot = path.resolve(targetRoot);
  const port = DEFAULT_PORT;

  const server = http.createServer((req, res) => {
    const url = new URL(req.url ?? "/", `http://localhost:${port}`);

    // API: list results
    if (url.pathname === "/api/results") {
      const resultsDir = path.join(absRoot, "results");
      if (!fs.existsSync(resultsDir)) {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end("[]");
        return;
      }
      const ids = fs
        .readdirSync(resultsDir, { withFileTypes: true })
        .filter((d) => d.isDirectory())
        .map((d) => d.name)
        .sort()
        .reverse();
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify(ids));
      return;
    }

    // API: get result by test ID
    const resultMatch = url.pathname.match(/^\/api\/results\/(.+)$/);
    if (resultMatch) {
      const testId = resultMatch[1];
      const metaPath = path.join(absRoot, "results", testId, "meta.json");
      if (!fs.existsSync(metaPath)) {
        res.writeHead(404, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "Not found" }));
        return;
      }
      // Return the full result structure
      try {
        const { loadTestResult } =
          require("../harness/runResult.js") as typeof import("../harness/runResult.js");
        const result = loadTestResult(testId);
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify(result));
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        res.writeHead(500, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: msg }));
      }
      return;
    }

    // Static file serving
    res.writeHead(200, { "Content-Type": "text/html" });
    res.end(
      "<html><body><h1>Pixie QA Web UI</h1><p>API available at /api/results</p></body></html>",
    );
  });

  server.listen(port, "127.0.0.1", () => {
    console.log(`Pixie web UI running at http://127.0.0.1:${port}`);
  });

  return 0;
}
