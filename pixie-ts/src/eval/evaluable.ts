/**
 * Evaluable model — uniform data carrier for evaluators.
 *
 * TestCase defines the scenario (input, expectation, metadata) without
 * the actual output. Evaluable extends it with actual output.
 * NamedData provides a name+value pair for structured evaluation data.
 */

import { z } from "zod";

/** JSON-compatible value type */
export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

/** Sentinel to distinguish "not provided" from null. */
export const UNSET = Symbol("UNSET");
export type Unset = typeof UNSET;

/** A named data value for evaluation input/output. */
export interface NamedData {
  readonly name: string;
  readonly value: JsonValue;
}

export const NamedDataSchema = z.object({
  name: z.string(),
  value: z.any(),
});

/** Scenario definition without actual output. */
export interface TestCase {
  readonly evalInput: NamedData[];
  readonly expectation: JsonValue | Unset;
  readonly evalMetadata: Record<string, JsonValue> | null;
  readonly description: string | null;
}

/** TestCase plus actual output — the full data carrier for evaluators. */
export interface Evaluable extends TestCase {
  readonly evalOutput: NamedData[];
}

/**
 * Create a TestCase.
 */
export function createTestCase(opts: {
  evalInput?: NamedData[];
  expectation?: JsonValue | Unset;
  evalMetadata?: Record<string, JsonValue> | null;
  description?: string | null;
}): TestCase {
  return {
    evalInput: opts.evalInput ?? [],
    expectation: opts.expectation ?? UNSET,
    evalMetadata: opts.evalMetadata ?? null,
    description: opts.description ?? null,
  };
}

/**
 * Create an Evaluable. Validates that evalInput and evalOutput are non-empty.
 */
export function createEvaluable(opts: {
  evalInput: NamedData[];
  evalOutput: NamedData[];
  expectation?: JsonValue | Unset;
  evalMetadata?: Record<string, JsonValue> | null;
  description?: string | null;
}): Evaluable {
  if (opts.evalInput.length === 0) {
    throw new Error("evalInput must be non-empty for Evaluable");
  }
  if (opts.evalOutput.length === 0) {
    throw new Error("evalOutput must be non-empty for Evaluable");
  }
  return {
    evalInput: opts.evalInput,
    evalOutput: opts.evalOutput,
    expectation: opts.expectation ?? UNSET,
    evalMetadata: opts.evalMetadata ?? null,
    description: opts.description ?? null,
  };
}

/**
 * Collapse a list of NamedData into a single JSON value.
 * - Empty list → null
 * - Single item → that item's value
 * - Multiple items → dict mapping name → value
 */
export function collapseNamedData(items: NamedData[]): JsonValue {
  if (items.length === 0) return null;
  if (items.length === 1) return items[0].value;
  const result: Record<string, JsonValue> = {};
  for (const item of items) {
    result[item.name] = item.value;
  }
  return result;
}
