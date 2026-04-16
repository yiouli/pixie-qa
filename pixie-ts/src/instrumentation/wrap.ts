/**
 * pixie.instrumentation.wrap — data-oriented observation and wrapping API.
 */

import type { JsonValue } from "../eval/evaluable.js";
import { INPUT_DATA_KEY } from "./models.js";
import { AsyncLocalStorage } from "node:async_hooks";

export type Purpose = "input" | "output" | "state";

/** A single wrap() observation record. */
export interface WrappedData {
  readonly type: "wrap";
  readonly name: string;
  readonly purpose: Purpose;
  readonly data: JsonValue;
  readonly description: string | null;
  readonly traceId: string | null;
  readonly spanId: string | null;
}

/** Filter wrap entries by purpose. */
export function filterByPurpose(
  entries: WrappedData[],
  purposes: Set<string>,
): WrappedData[] {
  return entries.filter((e) => purposes.has(e.purpose));
}

/** Serialize data to a JSON-compatible value. */
export function serializeWrapData(data: unknown): JsonValue {
  return JSON.parse(JSON.stringify(data)) as JsonValue;
}

/** Deserialize a JSON-compatible value. */
export function deserializeWrapData(data: JsonValue): unknown {
  return data;
}

// ── Context-variable registries ──────────────────────────────────────

interface WrapContext {
  evalInput: Map<string, JsonValue> | null;
  evalOutput: Array<Record<string, unknown>> | null;
}

const _wrapStorage = new AsyncLocalStorage<WrapContext>();

function getCtx(): WrapContext {
  return _wrapStorage.getStore() ?? { evalInput: null, evalOutput: null };
}

export function setEvalInput(registry: Map<string, JsonValue>): void {
  const ctx = getCtx();
  ctx.evalInput = registry;
}

export function getEvalInput(): Map<string, JsonValue> | null {
  return getCtx().evalInput;
}

export function clearEvalInput(): void {
  const ctx = getCtx();
  ctx.evalInput = null;
}

export function initEvalOutput(): Array<Record<string, unknown>> {
  const ctx = getCtx();
  const out: Array<Record<string, unknown>> = [];
  ctx.evalOutput = out;
  return out;
}

export function getEvalOutput(): Array<Record<string, unknown>> | null {
  return getCtx().evalOutput;
}

export function clearEvalOutput(): void {
  const ctx = getCtx();
  ctx.evalOutput = null;
}

/** Run a function within a wrap context. */
export function runWithWrapContext<T>(fn: () => T): T {
  return _wrapStorage.run({ evalInput: null, evalOutput: null }, fn);
}

/** Run an async function within a wrap context. */
export function runWithWrapContextAsync<T>(fn: () => Promise<T>): Promise<T> {
  return _wrapStorage.run({ evalInput: null, evalOutput: null }, fn);
}

// ── Exception types ──────────────────────────────────────────────────

export class WrapRegistryMissError extends Error {
  public readonly wrapName: string;
  constructor(name: string) {
    super(
      `wrap(name=${JSON.stringify(name)}, purpose='input') not found in eval registry. ` +
        `Ensure the dataset entry has a value for ${JSON.stringify(name)} in its input data.`,
    );
    this.name = "WrapRegistryMissError";
    this.wrapName = name;
  }
}

export class WrapTypeMismatchError extends TypeError {
  public readonly wrapName: string;
  constructor(name: string, expectedType: string, actualType: string) {
    super(
      `wrap(name=${JSON.stringify(name)}): expected type ${expectedType}, ` +
        `got ${actualType} from registry.`,
    );
    this.name = "WrapTypeMismatchError";
    this.wrapName = name;
  }
}

export class WrapNameCollisionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "WrapNameCollisionError";
  }
}

// ── wrap() API ──────────────────────────────────────────────────────

/**
 * Observe data at a named point.
 *
 * - purpose="input": inject from eval registry
 * - purpose="output"/"state": emit event and return data as-is
 */
export function wrap<T>(
  data: T,
  opts: {
    purpose: Purpose;
    name: string;
    description?: string;
  },
): T {
  const { purpose, name, description } = opts;

  if (purpose === "input") {
    const registry = getEvalInput();
    if (registry !== null) {
      if (!registry.has(name)) {
        throw new WrapRegistryMissError(name);
      }
      return registry.get(name) as T;
    }
    return data;
  }

  // purpose = "output" or "state"
  const body: Record<string, unknown> = {
    type: "wrap",
    name,
    purpose,
    data: serializeWrapData(data),
    description: description ?? null,
    traceId: null,
    spanId: null,
  };

  const evalOutput = getEvalOutput();
  if (evalOutput !== null) {
    evalOutput.push(body);
  }

  return data;
}
