/**
 * DatasetStore — JSON-file-backed CRUD for Dataset objects.
 *
 * Each dataset is stored as `<datasetDir>/<slug>.json`.
 * The directory is created on first write if it does not exist.
 */

import fs from "fs";
import path from "path";

import { getConfig } from "../config";
import type { Evaluable, JsonValue } from "../storage/evaluable";
import { UNSET } from "../storage/evaluable";
import type { Dataset } from "./models";

// ── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Convert a dataset name to a filesystem-safe slug.
 *
 * Lowercase, replace non-alphanumeric runs with `-`, strip leading/trailing `-`.
 */
export function _slugify(name: string): string {
  const slug = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  if (!slug) {
    throw new Error(
      `Cannot slugify empty or non-alphanumeric name: ${JSON.stringify(name)}`
    );
  }
  return slug;
}

function timestampToIso(ts: number): string {
  const d = new Date(ts);
  // Format: YYYY-MM-DD HH:MM:SS
  return d.toISOString().replace("T", " ").replace(/\.\d{3}Z$/, "");
}

// ── Serialization helpers ────────────────────────────────────────────────────

function evaluableToJson(ev: Evaluable): Record<string, JsonValue> {
  const obj: Record<string, JsonValue> = {
    evalInput: ev.evalInput,
    evalOutput: ev.evalOutput,
    evalMetadata: ev.evalMetadata,
    expectedOutput:
      ev.expectedOutput === UNSET ? null : (ev.expectedOutput as JsonValue),
    evaluators: ev.evaluators as JsonValue,
    description: ev.description,
  };
  return obj;
}

function jsonToEvaluable(raw: Record<string, unknown>): Evaluable {
  return {
    evalInput: (raw["evalInput"] ?? raw["eval_input"] ?? null) as JsonValue,
    evalOutput: (raw["evalOutput"] ?? raw["eval_output"] ?? null) as JsonValue,
    evalMetadata:
      (raw["evalMetadata"] ??
        raw["eval_metadata"] ??
        null) as Record<string, JsonValue> | null,
    expectedOutput:
      raw["expectedOutput"] !== undefined
        ? (raw["expectedOutput"] as JsonValue)
        : raw["expected_output"] !== undefined
          ? (raw["expected_output"] as JsonValue)
          : UNSET,
    evaluators: (raw["evaluators"] as readonly string[] | null) ?? null,
    description: (raw["description"] as string | null) ?? null,
  };
}

// ── DatasetStore ─────────────────────────────────────────────────────────────

export class DatasetStore {
  private readonly _dir: string;

  constructor(datasetDir?: string) {
    this._dir = datasetDir ?? getConfig().datasetDir;
  }

  private _pathFor(name: string): string {
    return path.join(this._dir, `${_slugify(name)}.json`);
  }

  private _ensureDir(): void {
    fs.mkdirSync(this._dir, { recursive: true });
  }

  private _write(filePath: string, dataset: Dataset): void {
    this._ensureDir();
    const data = {
      name: dataset.name,
      items: dataset.items.map(evaluableToJson),
    };
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + "\n", "utf-8");
  }

  private _read(filePath: string): Dataset {
    const raw = JSON.parse(fs.readFileSync(filePath, "utf-8"));
    return {
      name: raw.name as string,
      items: (raw.items as Record<string, unknown>[]).map(jsonToEvaluable),
    };
  }

  // ── CRUD ──────────────────────────────────────────────────────────────

  /**
   * Create a new dataset.
   * @throws if a dataset with the same name already exists.
   */
  create(name: string, items?: Evaluable[]): Dataset {
    const filePath = this._pathFor(name);
    if (fs.existsSync(filePath)) {
      throw new Error(`Dataset already exists: ${JSON.stringify(name)}`);
    }
    const dataset: Dataset = { name, items: items ?? [] };
    this._write(filePath, dataset);
    return dataset;
  }

  /**
   * Load a dataset by name.
   * @throws if the dataset does not exist.
   */
  get(name: string): Dataset {
    const filePath = this._pathFor(name);
    if (!fs.existsSync(filePath)) {
      throw new Error(`Dataset not found: ${JSON.stringify(name)}`);
    }
    return this._read(filePath);
  }

  /** Return the names of all stored datasets. */
  list(): string[] {
    if (!fs.existsSync(this._dir)) return [];
    const names: string[] = [];
    const files = fs.readdirSync(this._dir).filter((f) => f.endsWith(".json")).sort();
    for (const f of files) {
      try {
        const ds = this._read(path.join(this._dir, f));
        names.push(ds.name);
      } catch {
        continue; // skip malformed files
      }
    }
    return names;
  }

  /** Return metadata for every stored dataset. */
  listDetails(): Array<Record<string, unknown>> {
    if (!fs.existsSync(this._dir)) return [];
    const rows: Array<Record<string, unknown>> = [];
    const files = fs.readdirSync(this._dir).filter((f) => f.endsWith(".json")).sort();
    for (const f of files) {
      try {
        const filePath = path.join(this._dir, f);
        const ds = this._read(filePath);
        const stat = fs.statSync(filePath);
        rows.push({
          name: ds.name,
          rowCount: ds.items.length,
          createdAt: timestampToIso(stat.birthtimeMs),
          updatedAt: timestampToIso(stat.mtimeMs),
        });
      } catch {
        continue; // skip malformed files
      }
    }
    return rows;
  }

  /**
   * Delete a dataset by name.
   * @throws if the dataset does not exist.
   */
  delete(name: string): void {
    const filePath = this._pathFor(name);
    if (!fs.existsSync(filePath)) {
      throw new Error(`Dataset not found: ${JSON.stringify(name)}`);
    }
    fs.unlinkSync(filePath);
  }

  /** Append items to an existing dataset. */
  append(name: string, ...items: Evaluable[]): Dataset {
    const dataset = this.get(name);
    const updated: Dataset = {
      name: dataset.name,
      items: [...dataset.items, ...items],
    };
    this._write(this._pathFor(name), updated);
    return updated;
  }

  /**
   * Remove an item by index from an existing dataset.
   * @throws if the dataset does not exist or index is out of range.
   */
  remove(name: string, index: number): Dataset {
    const dataset = this.get(name);
    const items = [...dataset.items];
    if (index < 0 || index >= items.length) {
      throw new RangeError(
        `Index ${index} out of range for dataset ${JSON.stringify(name)} with ${items.length} items`
      );
    }
    items.splice(index, 1);
    const updated: Dataset = { name: dataset.name, items };
    this._write(this._pathFor(name), updated);
    return updated;
  }
}
