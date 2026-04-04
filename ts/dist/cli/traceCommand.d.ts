/**
 * `pixie-qa trace` CLI subcommands — list, show, last, verify.
 *
 * Provides read-only inspection of captured traces via the ObservationStore.
 */
/**
 * Entry point for `pixie-qa trace list`.
 */
export declare function traceList(limit?: number, errorsOnly?: boolean): number;
/**
 * Entry point for `pixie-qa trace show`.
 */
export declare function traceShow(traceId: string, verbose?: boolean, asJson?: boolean): number;
/**
 * Entry point for `pixie-qa trace last`.
 */
export declare function traceLast(asJson?: boolean): number;
/**
 * Entry point for `pixie-qa trace verify`.
 */
export declare function traceVerify(): number;
//# sourceMappingURL=traceCommand.d.ts.map