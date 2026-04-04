/**
 * In-memory trace capture for eval test execution.
 *
 * Provides `MemoryTraceHandler` that collects spans into a list, and
 * `captureTraces()` — a callback-based wrapper (replacing Python's
 * context manager) for scoped trace capture during tests.
 */

import {
  init,
  addHandler,
  removeHandler,
  flush,
  InstrumentationHandler,
} from "../instrumentation";
import type { LLMSpan, ObserveSpan } from "../instrumentation/spans";
import { ObservationNode, buildTree } from "../storage/tree";

// ── MemoryTraceHandler ───────────────────────────────────────────────────────

/**
 * Collects ObserveSpan and LLMSpan instances into an in-memory list.
 *
 * Used by the eval test runner to capture traces without writing to disk.
 */
export class MemoryTraceHandler extends InstrumentationHandler {
  spans: Array<ObserveSpan | LLMSpan> = [];

  override async onLlm(span: LLMSpan): Promise<void> {
    this.spans.push(span);
  }

  override async onObserve(span: ObserveSpan): Promise<void> {
    this.spans.push(span);
  }

  /** Filter spans by traceId and build the tree. */
  getTrace(traceId: string): ObservationNode[] {
    const matching = this.spans.filter((s) => s.traceId === traceId);
    return buildTree(matching);
  }

  /** Group all captured spans by traceId and build trees. */
  getAllTraces(): Map<string, ObservationNode[]> {
    const byTrace = new Map<string, Array<ObserveSpan | LLMSpan>>();
    for (const s of this.spans) {
      let list = byTrace.get(s.traceId);
      if (!list) {
        list = [];
        byTrace.set(s.traceId, list);
      }
      list.push(s);
    }
    const result = new Map<string, ObservationNode[]>();
    for (const [tid, spans] of byTrace.entries()) {
      result.set(tid, buildTree(spans));
    }
    return result;
  }

  /** Remove all collected spans. */
  clear(): void {
    this.spans.length = 0;
  }
}

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
export async function captureTraces<T>(
  callback: (handler: MemoryTraceHandler) => T | Promise<T>
): Promise<{ result: T; handler: MemoryTraceHandler }> {
  init();
  const handler = new MemoryTraceHandler();
  addHandler(handler);
  try {
    const result = await callback(handler);
    return { result, handler };
  } finally {
    await flush();
    removeHandler(handler);
  }
}
