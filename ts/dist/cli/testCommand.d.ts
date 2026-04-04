/**
 * `pixie-qa test` CLI entry point.
 *
 * Usage:
 *   pixie-qa test [path] [--verbose] [--no-open]
 *
 * Dataset mode — when `path` is a `.json` file or a directory
 * containing dataset JSON files. Each dataset produces its own result.
 * Default — no path searches the pixie datasets directory.
 */
/**
 * Main entry point for `pixie-qa test`.
 *
 * @returns Exit code: 0 if all tests pass, 1 otherwise.
 */
export declare function testMain(opts: {
    path?: string;
    verbose?: boolean;
    noOpen?: boolean;
}): Promise<number>;
//# sourceMappingURL=testCommand.d.ts.map