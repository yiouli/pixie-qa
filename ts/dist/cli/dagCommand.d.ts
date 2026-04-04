/**
 * `pixie-qa dag` CLI subcommands — validate and check-trace.
 *
 * Commands:
 *   pixie-qa dag validate <json_file> [--project-root PATH]
 *   pixie-qa dag check-trace <json_file>
 */
/**
 * Validate a DAG JSON file and generate a Mermaid diagram.
 *
 * @returns Exit code: 0 on success, 1 on validation failure.
 */
export declare function dagValidate(jsonFile: string, projectRoot?: string): number;
/**
 * Check the last captured trace against a DAG JSON file.
 *
 * @returns Exit code: 0 if trace matches, 1 otherwise.
 */
export declare function dagCheckTrace(jsonFile: string): Promise<number>;
//# sourceMappingURL=dagCommand.d.ts.map