/**
 * `pixie-qa dataset` CLI commands.
 *
 * Provides operations for managing datasets and saving trace spans
 * as evaluable items:
 *
 * - `datasetCreate` — create a new empty dataset.
 * - `datasetList` — list datasets with basic information.
 * - `datasetSave` — select a span from the latest trace and save it.
 */

import type { Dataset } from "../dataset/models";
import { DatasetStore } from "../dataset/store";
import type { Evaluable, JsonValue } from "../storage/evaluable";
import { UNSET, asEvaluable } from "../storage/evaluable";
import type { Unset } from "../storage/evaluable";
import { ObservationStore } from "../storage/store";
import { getConfig } from "../config";

/**
 * Create a new empty dataset.
 */
export function datasetCreate(
  name: string,
  datasetStore?: DatasetStore
): Dataset {
  const store = datasetStore ?? new DatasetStore();
  return store.create(name);
}

/**
 * Return metadata for every dataset.
 */
export function datasetList(
  datasetStore?: DatasetStore
): Array<Record<string, unknown>> {
  const store = datasetStore ?? new DatasetStore();
  return store.listDetails();
}

/**
 * Format dataset metadata rows as an aligned CLI table.
 */
export function formatDatasetTable(
  rows: Array<Record<string, unknown>>
): string {
  if (rows.length === 0) return "No datasets found.";

  const headers = ["Name", "Rows", "Created", "Updated"];
  const data = rows.map((r) => [
    String(r["name"]),
    String(r["rowCount"] ?? r["row_count"] ?? 0),
    String(r["createdAt"] ?? r["created_at"] ?? ""),
    String(r["updatedAt"] ?? r["updated_at"] ?? ""),
  ]);

  const colWidths = headers.map((h) => h.length);
  for (const row of data) {
    for (let i = 0; i < row.length; i++) {
      colWidths[i] = Math.max(colWidths[i], row[i].length);
    }
  }

  const fmtRow = (cells: string[]): string =>
    cells.map((c, i) => c.padEnd(colWidths[i])).join("  ");

  const lines = [
    fmtRow(headers),
    fmtRow(colWidths.map((w) => "-".repeat(w))),
    ...data.map(fmtRow),
  ];
  return lines.join("\n");
}

/**
 * Select a span from the latest trace and save it to a dataset.
 */
export function datasetSave(opts: {
  name: string;
  select?: string;
  spanName?: string;
  expectedOutput?: JsonValue | Unset;
  notes?: string;
}): Dataset {
  const config = getConfig();
  const obsStore = new ObservationStore(config.dbPath);
  const dsStore = new DatasetStore();

  try {
    obsStore.createTables();
    const traces = obsStore.listTraces(1);
    if (traces.length === 0) {
      throw new Error("No traces found in the observation store.");
    }
    const traceId = traces[0]["traceId"] as string;

    const select = opts.select ?? "root";
    let span;

    if (select === "root") {
      span = obsStore.getRoot(traceId);
    } else if (select === "last_llm_call") {
      span = obsStore.getLastLlm(traceId);
      if (span === null) {
        throw new Error(`No LLM span found in trace ${traceId}.`);
      }
    } else if (select === "by_name") {
      if (!opts.spanName) {
        throw new Error("--span-name is required when selection mode is 'by_name'.");
      }
      const matches = obsStore.getByName(opts.spanName, traceId);
      if (matches.length === 0) {
        throw new Error(
          `No span named '${opts.spanName}' found in trace ${traceId}.`
        );
      }
      span = matches[matches.length - 1];
    } else {
      throw new Error(`Unknown selection mode: '${select}'`);
    }

    let evaluable: Evaluable = asEvaluable(span);

    // Apply expected_output if provided
    const expectedOutput = opts.expectedOutput ?? UNSET;
    if (expectedOutput !== UNSET) {
      evaluable = {
        ...evaluable,
        expectedOutput: expectedOutput as JsonValue,
      };
    }

    // Apply notes if provided
    if (opts.notes !== undefined) {
      const existingMeta = evaluable.evalMetadata
        ? { ...evaluable.evalMetadata }
        : {};
      existingMeta["notes"] = opts.notes;
      evaluable = {
        ...evaluable,
        evalMetadata: existingMeta,
      };
    }

    return dsStore.append(opts.name, evaluable);
  } finally {
    obsStore.close();
  }
}
