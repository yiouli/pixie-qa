"use strict";
/**
 * In-memory trace capture for eval test execution.
 *
 * Provides `MemoryTraceHandler` that collects spans into a list, and
 * `captureTraces()` — a callback-based wrapper (replacing Python's
 * context manager) for scoped trace capture during tests.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.MemoryTraceHandler = void 0;
exports.captureTraces = captureTraces;
const instrumentation_1 = require("../instrumentation");
const tree_1 = require("../storage/tree");
// ── MemoryTraceHandler ───────────────────────────────────────────────────────
/**
 * Collects ObserveSpan and LLMSpan instances into an in-memory list.
 *
 * Used by the eval test runner to capture traces without writing to disk.
 */
class MemoryTraceHandler extends instrumentation_1.InstrumentationHandler {
    spans = [];
    async onLlm(span) {
        this.spans.push(span);
    }
    async onObserve(span) {
        this.spans.push(span);
    }
    /** Filter spans by traceId and build the tree. */
    getTrace(traceId) {
        const matching = this.spans.filter((s) => s.traceId === traceId);
        return (0, tree_1.buildTree)(matching);
    }
    /** Group all captured spans by traceId and build trees. */
    getAllTraces() {
        const byTrace = new Map();
        for (const s of this.spans) {
            let list = byTrace.get(s.traceId);
            if (!list) {
                list = [];
                byTrace.set(s.traceId, list);
            }
            list.push(s);
        }
        const result = new Map();
        for (const [tid, spans] of byTrace.entries()) {
            result.set(tid, (0, tree_1.buildTree)(spans));
        }
        return result;
    }
    /** Remove all collected spans. */
    clear() {
        this.spans.length = 0;
    }
}
exports.MemoryTraceHandler = MemoryTraceHandler;
// ── captureTraces ────────────────────────────────────────────────────────────
/**
 * Capture traces during callback execution.
 *
 * Replaces Python's `capture_traces()` context manager with a callback
 * pattern. Installs a MemoryTraceHandler, runs the callback, flushes
 * the delivery queue, then removes the handler.
 *
 * @returns The handler with all captured spans.
 */
async function captureTraces(callback) {
    (0, instrumentation_1.init)();
    const handler = new MemoryTraceHandler();
    (0, instrumentation_1.addHandler)(handler);
    try {
        const result = await callback(handler);
        return { result, handler };
    }
    finally {
        await (0, instrumentation_1.flush)();
        (0, instrumentation_1.removeHandler)(handler);
    }
}
//# sourceMappingURL=traceCapture.js.map