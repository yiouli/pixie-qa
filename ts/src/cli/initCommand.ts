/**
 * `pixie-qa init` — scaffold the pixie_qa working directory.
 *
 * Creates the standard directory layout for eval-driven development:
 *   pixie_qa/
 *     datasets/
 *     tests/
 *     scripts/
 *
 * The command is idempotent: existing files and directories are never
 * overwritten or deleted.
 */

import fs from "fs";
import path from "path";

import { getConfig } from "../config";

/** Subdirectories to create under the pixie root. */
const SUBDIRS = ["datasets", "tests", "scripts"];

/**
 * Create the pixie working directory and its standard layout.
 *
 * @param root - Override for the pixie root directory. When undefined,
 *   uses the value from `getConfig()` (respects `PIXIE_ROOT` env var,
 *   defaults to `pixie_qa`).
 * @returns The resolved path of the root directory.
 */
export function initPixieDir(root?: string): string {
  if (root === undefined) {
    root = getConfig().root;
  }

  const rootPath = path.resolve(root);
  fs.mkdirSync(rootPath, { recursive: true });

  for (const subdir of SUBDIRS) {
    fs.mkdirSync(path.join(rootPath, subdir), { recursive: true });
  }

  return rootPath;
}
