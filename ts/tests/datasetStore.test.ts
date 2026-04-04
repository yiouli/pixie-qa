import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "fs";
import path from "path";
import os from "os";
import { DatasetStore } from "../src/dataset/store";
import { UNSET } from "../src/storage/evaluable";
import type { Evaluable } from "../src/storage/evaluable";

// ── Test helpers ─────────────────────────────────────────────────────────────

function makeEvaluable(overrides: Partial<Evaluable> = {}): Evaluable {
  return {
    evalInput: "What is AI?",
    evalOutput: "Artificial Intelligence",
    evalMetadata: null,
    expectedOutput: UNSET,
    evaluators: null,
    description: null,
    ...overrides,
  };
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("DatasetStore", () => {
  let testDir: string;
  let store: DatasetStore;

  beforeEach(() => {
    testDir = fs.mkdtempSync(path.join(os.tmpdir(), "pixie-ds-test-"));
    store = new DatasetStore(testDir);
  });

  afterEach(() => {
    fs.rmSync(testDir, { recursive: true, force: true });
  });

  describe("create", () => {
    it("creates a new empty dataset", () => {
      const ds = store.create("My Dataset");
      expect(ds.name).toBe("My Dataset");
      expect(ds.items).toHaveLength(0);
    });

    it("creates a dataset with initial items", () => {
      const items = [makeEvaluable(), makeEvaluable({ evalInput: "Q2" })];
      const ds = store.create("With Items", items);
      expect(ds.items).toHaveLength(2);
    });

    it("throws when dataset already exists", () => {
      store.create("Unique");
      expect(() => store.create("Unique")).toThrow("already exists");
    });

    it("persists to disk as JSON", () => {
      store.create("Persisted");
      const filePath = path.join(testDir, "persisted.json");
      expect(fs.existsSync(filePath)).toBe(true);
      const raw = JSON.parse(fs.readFileSync(filePath, "utf-8"));
      expect(raw.name).toBe("Persisted");
    });
  });

  describe("get", () => {
    it("retrieves a stored dataset", () => {
      store.create("Test DS", [makeEvaluable()]);
      const ds = store.get("Test DS");
      expect(ds.name).toBe("Test DS");
      expect(ds.items).toHaveLength(1);
    });

    it("throws when dataset does not exist", () => {
      expect(() => store.get("Missing")).toThrow("not found");
    });

    it("round-trips evaluable data correctly", () => {
      const item = makeEvaluable({
        evalInput: "question",
        evalOutput: "answer",
        evalMetadata: { key: "val" },
        expectedOutput: "expected",
        description: "test item",
      });
      store.create("Round Trip", [item]);
      const ds = store.get("Round Trip");
      expect(ds.items[0].evalInput).toBe("question");
      expect(ds.items[0].evalOutput).toBe("answer");
      expect(ds.items[0].expectedOutput).toBe("expected");
      expect(ds.items[0].description).toBe("test item");
    });
  });

  describe("list", () => {
    it("returns empty array when no datasets exist", () => {
      expect(store.list()).toEqual([]);
    });

    it("returns names of all stored datasets", () => {
      store.create("Alpha");
      store.create("Beta");
      const names = store.list();
      expect(names).toContain("Alpha");
      expect(names).toContain("Beta");
      expect(names).toHaveLength(2);
    });
  });

  describe("append", () => {
    it("appends items to an existing dataset", () => {
      store.create("Appendable", [makeEvaluable()]);
      const updated = store.append("Appendable", makeEvaluable({ evalInput: "new" }));
      expect(updated.items).toHaveLength(2);
      // Verify persistence
      const ds = store.get("Appendable");
      expect(ds.items).toHaveLength(2);
    });

    it("throws when dataset does not exist", () => {
      expect(() => store.append("Missing", makeEvaluable())).toThrow(
        "not found"
      );
    });
  });

  describe("remove", () => {
    it("removes an item by index", () => {
      store.create("Removable", [
        makeEvaluable({ evalInput: "first" }),
        makeEvaluable({ evalInput: "second" }),
        makeEvaluable({ evalInput: "third" }),
      ]);
      const updated = store.remove("Removable", 1);
      expect(updated.items).toHaveLength(2);
      expect(updated.items[0].evalInput).toBe("first");
      expect(updated.items[1].evalInput).toBe("third");
    });

    it("throws on out-of-range index", () => {
      store.create("Small", [makeEvaluable()]);
      expect(() => store.remove("Small", 5)).toThrow("out of range");
    });

    it("throws on negative index", () => {
      store.create("Small2", [makeEvaluable()]);
      expect(() => store.remove("Small2", -1)).toThrow("out of range");
    });
  });

  describe("delete", () => {
    it("deletes a dataset by name", () => {
      store.create("ToDelete");
      store.delete("ToDelete");
      expect(() => store.get("ToDelete")).toThrow("not found");
    });

    it("throws when dataset does not exist", () => {
      expect(() => store.delete("Ghost")).toThrow("not found");
    });
  });
});
