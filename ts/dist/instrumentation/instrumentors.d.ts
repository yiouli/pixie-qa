/**
 * Auto-discovers and activates known LLM instrumentor packages.
 *
 * Tries to `require()` known OpenInference instrumentor packages
 * and activate them. Missing packages are silently skipped.
 */
/**
 * Try to instrument all known LLM providers.
 * @returns List of activated instrumentor class names.
 */
export declare function activateInstrumentors(): string[];
//# sourceMappingURL=instrumentors.d.ts.map