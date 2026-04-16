/**
 * Runnable interface for dataset-driven evaluation.
 */

import { z } from "zod";

/**
 * Protocol for structured runnables used by the evaluation harness.
 *
 * Lifecycle:
 * 1. create() — constructs a single runnable instance
 * 2. setup() — called once before any entries run
 * 3. run(args) — called concurrently for each dataset entry
 * 4. teardown() — called once after all entries finish
 */
export interface Runnable<T = unknown> {
  setup(): Promise<void>;
  teardown(): Promise<void>;
  run(args: T): Promise<void>;
}

export interface RunnableClass<T = unknown> {
  create(): Runnable<T>;
}

/**
 * Check whether an object has a static `create` method and a `run` method
 * on its prototype, matching the Runnable protocol shape.
 */
export function isRunnableClass(obj: unknown): obj is RunnableClass {
  if (typeof obj !== "function") return false;
  const proto = (obj as unknown as { prototype?: unknown }).prototype;
  return (
    typeof (obj as unknown as Record<string, unknown>).create === "function" &&
    proto !== undefined &&
    typeof (proto as Record<string, unknown>).run === "function"
  );
}

/**
 * Extract the Zod schema from a Runnable class's static argsSchema property,
 * or null if not present.
 */
export function getRunnableArgsSchema(
  runnableClass: RunnableClass,
): z.ZodType | null {
  const schema = (runnableClass as unknown as Record<string, unknown>)[
    "argsSchema"
  ];
  if (schema && typeof (schema as z.ZodType).parse === "function") {
    return schema as z.ZodType;
  }
  return null;
}
