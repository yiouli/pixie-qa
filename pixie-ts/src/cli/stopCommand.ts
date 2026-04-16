/**
 * pixie stop — stop the running web UI server.
 */

import fs from "node:fs";
import path from "node:path";
import { getConfig } from "../config.js";

export function stop(root?: string | null): number {
  const config = getConfig();
  const targetRoot = root ?? config.root;
  const lockPath = path.join(path.resolve(targetRoot), "server.lock");

  if (!fs.existsSync(lockPath)) {
    console.log("No running server found.");
    return 0;
  }

  try {
    const lockData = JSON.parse(fs.readFileSync(lockPath, "utf-8")) as Record<
      string,
      unknown
    >;
    const pid = lockData["pid"] as number | undefined;
    if (pid) {
      try {
        process.kill(pid, "SIGTERM");
        console.log(`Stopped server (PID ${pid}).`);
      } catch {
        console.log("Server process not found (may have already stopped).");
      }
    }
    fs.unlinkSync(lockPath);
  } catch {
    console.log("No running server found.");
  }

  return 0;
}
