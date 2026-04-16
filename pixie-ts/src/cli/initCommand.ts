/**
 * pixie init — scaffold the pixie_qa working directory.
 */

import fs from "node:fs";
import path from "node:path";
import { getConfig } from "../config.js";

export function initPixieDir(root?: string | null): string {
  const config = getConfig();
  const targetRoot = root ?? config.root;
  const absRoot = path.resolve(targetRoot);

  fs.mkdirSync(path.join(absRoot, "datasets"), { recursive: true });
  fs.mkdirSync(path.join(absRoot, "results"), { recursive: true });

  return absRoot;
}
