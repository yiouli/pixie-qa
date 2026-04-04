/**
 * Pre-made span handlers for common persistence patterns.
 *
 * Provides `StorageHandler` — an async handler that writes spans to
 * a storage backend — and the `enableStorage()` convenience function
 * for zero-config setup.
 */

import { getConfig } from "../config";
import { InstrumentationHandler } from "./handler";
import { addHandler, init } from "./observation";
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
export class StorageHandler extends InstrumentationHandler {
  readonly store: ObservationStore;

  constructor(store: ObservationStore) {
    super();
    this.store = store;
  }

  override async onLlm(span: LLMSpan): Promise<void> {
    try {
      await this.store.save(span);
    } catch {
      // silently swallowed
    }
  }

  override async onObserve(span: ObserveSpan): Promise<void> {
    try {
      await this.store.save(span);
    } catch {
      // silently swallowed
    }
  }
}

let _storageHandler: StorageHandler | null = null;

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
export async function enableStorage(
  storeFactory: (dbPath: string) => ObservationStore
): Promise<StorageHandler> {
  if (_storageHandler) {
    return _storageHandler;
  }

  init();

  const config = getConfig();

  // Ensure root directory exists
  const fs = await import("fs");
  const path = await import("path");
  const dbDir = path.dirname(config.dbPath);
  if (dbDir) {
    fs.mkdirSync(dbDir, { recursive: true });
  }

  const store = storeFactory(config.dbPath);
  await store.createTables();
  const handler = new StorageHandler(store);

  addHandler(handler);
  _storageHandler = handler;
  return handler;
}

/**
 * Reset the module-level handler. **Test-only** — not part of the public API.
 * @internal
 */
export function _resetStorageHandler(): void {
  _storageHandler = null;
}
