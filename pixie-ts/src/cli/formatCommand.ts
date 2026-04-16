/**
 * pixie format — convert a trace log into a dataset entry JSON object.
 */

import fs from "node:fs";
import path from "node:path";
import type { JsonValue } from "../eval/evaluable.js";

export function formatTraceToEntry(
  inputPath: string,
  outputPath: string,
): void {
  const absInput = path.resolve(inputPath);
  if (!fs.existsSync(absInput)) {
    throw new Error(`Input file not found: ${absInput}`);
  }

  const lines = fs
    .readFileSync(absInput, "utf-8")
    .split("\n")
    .filter((l) => l.trim());

  let inputData: Record<string, JsonValue> = {};
  const evalInput: Array<{ name: string; value: JsonValue }> = [];
  const evalOutput: Array<{ name: string; value: JsonValue }> = [];

  for (const line of lines) {
    const record = JSON.parse(line) as Record<string, unknown>;
    const type = record["type"] as string;

    if (type === "kwargs") {
      inputData = record["value"] as Record<string, JsonValue>;
    } else if (type === "wrap") {
      const purpose = record["purpose"] as string;
      const name = record["name"] as string;
      const data = record["data"] as JsonValue;
      if (purpose === "input") {
        evalInput.push({ name, value: data });
      } else if (purpose === "output" || purpose === "state") {
        evalOutput.push({ name, value: data });
      }
    }
  }

  const entry: Record<string, unknown> = {
    input_data: inputData,
    description: "",
  };
  if (evalInput.length > 0) entry["eval_input"] = evalInput;
  if (evalOutput.length > 0) {
    // Include eval_output as reference for building expectations
    entry["_eval_output_preview"] = evalOutput;
  }

  const absOutput = path.resolve(outputPath);
  fs.mkdirSync(path.dirname(absOutput), { recursive: true });
  fs.writeFileSync(absOutput, JSON.stringify(entry, null, 2) + "\n", "utf-8");
  console.log(`Dataset entry written to: ${absOutput}`);
}
