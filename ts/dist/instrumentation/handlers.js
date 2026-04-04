"use strict";
/**
 * Pre-made span handlers for common persistence patterns.
 *
 * Provides `StorageHandler` — an async handler that writes spans to
 * a storage backend — and the `enableStorage()` convenience function
 * for zero-config setup.
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.StorageHandler = void 0;
exports.enableStorage = enableStorage;
exports._resetStorageHandler = _resetStorageHandler;
const config_1 = require("../config");
const handler_1 = require("./handler");
const observation_1 = require("./observation");
/**
 * Span handler that persists completed spans to an ObservationStore.
 *
 * Both `onLlm` and `onObserve` are async so `store.save()` is awaited
 * directly. Exceptions are silently swallowed to avoid crashing the
 * delivery pipeline.
 */
class StorageHandler extends handler_1.InstrumentationHandler {
    store;
    constructor(store) {
        super();
        this.store = store;
    }
    async onLlm(span) {
        try {
            await this.store.save(span);
        }
        catch {
            // silently swallowed
        }
    }
    async onObserve(span) {
        try {
            await this.store.save(span);
        }
        catch {
            // silently swallowed
        }
    }
}
exports.StorageHandler = StorageHandler;
let _storageHandler = null;
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
async function enableStorage(storeFactory) {
    if (_storageHandler) {
        return _storageHandler;
    }
    (0, observation_1.init)();
    const config = (0, config_1.getConfig)();
    // Ensure root directory exists
    const fs = await Promise.resolve().then(() => __importStar(require("fs")));
    const path = await Promise.resolve().then(() => __importStar(require("path")));
    const dbDir = path.dirname(config.dbPath);
    if (dbDir) {
        fs.mkdirSync(dbDir, { recursive: true });
    }
    const store = storeFactory(config.dbPath);
    await store.createTables();
    const handler = new StorageHandler(store);
    (0, observation_1.addHandler)(handler);
    _storageHandler = handler;
    return handler;
}
/**
 * Reset the module-level handler. **Test-only** — not part of the public API.
 * @internal
 */
function _resetStorageHandler() {
    _storageHandler = null;
}
//# sourceMappingURL=handlers.js.map