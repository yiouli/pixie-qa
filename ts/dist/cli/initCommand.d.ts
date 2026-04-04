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
/**
 * Create the pixie working directory and its standard layout.
 *
 * @param root - Override for the pixie root directory. When undefined,
 *   uses the value from `getConfig()` (respects `PIXIE_ROOT` env var,
 *   defaults to `pixie_qa`).
 * @returns The resolved path of the root directory.
 */
export declare function initPixieDir(root?: string): string;
//# sourceMappingURL=initCommand.d.ts.map