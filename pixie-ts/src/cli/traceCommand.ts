/**
 * pixie trace — run a Runnable and capture trace output to JSONL.
 */

import fs from "node:fs";
import path from "node:path";
import { resolveRunnableReference } from "../harness/runner.js";
import { isRunnableClass, type RunnableClass } from "../harness/runnable.js";
import type { JsonValue } from "../eval/evaluable.js";

export async function runTrace(opts: {
  runnable: string;
  inputPath: string;
  outputPath: string;
}): Promise<number> {
  // Load input kwargs
  const inputPath = path.resolve(opts.inputPath);
  if (!fs.existsSync(inputPath)) {
    console.error(`Input file not found: ${inputPath}`);
    return 1;
  }
  const kwargs = JSON.parse(fs.readFileSync(inputPath, "utf-8")) as Record<
    string,
    JsonValue
  >;

  // Ensure output directory exists
  const outputPath = path.resolve(opts.outputPath);
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });

  // Write input data as first line of JSONL
  const lines: string[] = [];
  lines.push(JSON.stringify({ type: "kwargs", value: kwargs }));

  try {
    const resolved = await resolveRunnableReference(opts.runnable);

    if (isRunnableClass(resolved)) {
      const instance = (resolved as RunnableClass).create();
      await instance.setup();
      try {
        await instance.run(kwargs);
      } finally {
        await instance.teardown();
      }
    } else if (typeof resolved === "function") {
      await (resolved as (args: Record<string, JsonValue>) => Promise<void>)(
        kwargs,
      );
    } else {
      console.error("Resolved runnable is not callable.");
      return 1;
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error(`Error running trace: ${msg}`);
    return 1;
  }

  fs.writeFileSync(outputPath, lines.join("\n") + "\n", "utf-8");
  console.log(`Trace written to: ${outputPath}`);
  return 0;
}
