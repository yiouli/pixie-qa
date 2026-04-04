"use strict";
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
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.initPixieDir = initPixieDir;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const config_1 = require("../config");
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
function initPixieDir(root) {
    if (root === undefined) {
        root = (0, config_1.getConfig)().root;
    }
    const rootPath = path_1.default.resolve(root);
    fs_1.default.mkdirSync(rootPath, { recursive: true });
    for (const subdir of SUBDIRS) {
        fs_1.default.mkdirSync(path_1.default.join(rootPath, subdir), { recursive: true });
    }
    return rootPath;
}
//# sourceMappingURL=initCommand.js.map