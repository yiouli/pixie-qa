/**
 * `pixie-qa analyze` CLI command.
 *
 * Generates analysis and recommendations for a test run result by
 * running an LLM agent (via OpenAI API) on each dataset's results.
 *
 * Usage:
 *   pixie-qa analyze <test_run_id>
 *
 * The analysis markdown is saved alongside the result JSON at
 * `<pixie_root>/results/<test_id>/dataset-<index>.md`.
 */
/**
 * Entry point for `pixie-qa analyze <test_run_id>`.
 */
export declare function analyze(testId: string): Promise<number>;
//# sourceMappingURL=analyzeCommand.d.ts.map