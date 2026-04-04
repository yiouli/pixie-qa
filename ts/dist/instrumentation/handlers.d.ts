/**
 * Pre-made span handlers for common persistence patterns.
 *
 * Provides `StorageHandler` — an async handler that writes spans to
 * a storage backend — and the `enableStorage()` convenience function
 * for zero-config setup.
 */
import { InstrumentationHandler } from "./handler";
import type { LLMSpan, ObserveSpan } from "./spans";
/**
 * Minimal storage interface for observation persistence.
 *
 * Concrete implementations (e.g. SQLite-backed) should implement this
 * interface.
 */
export interface ObservationStore {
    save(span: LLMSpan | ObserveSpan): Promise<void>;
    createTables(): Promise<void>;
}
/**
 * Span handler that persists completed spans to an ObservationStore.
 *
 * Both `onLlm` and `onObserve` are async so `store.save()` is awaited
 * directly. Exceptions are silently swallowed to avoid crashing the
 * delivery pipeline.
 */
export declare class StorageHandler extends InstrumentationHandler {
    readonly store: ObservationStore;
    constructor(store: ObservationStore);
    onLlm(span: LLMSpan): Promise<void>;
    onObserve(span: ObserveSpan): Promise<void>;
}
/**
 * Set up storage with default config and register the handler.
 *
 * Creates the observation table if it doesn't exist. Idempotent —
 * calling twice returns the same handler without duplicating
 * registrations.
 *
 * @param storeFactory - Factory function that creates an ObservationStore
 *   given the database path from config.
 * @returns The StorageHandler for optional manual control.
 */
export declare function enableStorage(storeFactory: (dbPath: string) => ObservationStore): Promise<StorageHandler>;
/**
 * Reset the module-level handler. **Test-only** — not part of the public API.
 * @internal
 */
export declare function _resetStorageHandler(): void;
//# sourceMappingURL=handlers.d.ts.map