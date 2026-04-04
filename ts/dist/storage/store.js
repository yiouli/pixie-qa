"use strict";
/**
 * ObservationStore — synchronous persistence and query API using better-sqlite3.
 *
 * Since better-sqlite3 is a synchronous driver, all methods are sync
 * (unlike the async Python version using Piccolo).
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.ObservationStore = void 0;
const better_sqlite3_1 = __importDefault(require("better-sqlite3"));
const serialization_1 = require("./serialization");
const tree_1 = require("./tree");
// ── SQL statements ───────────────────────────────────────────────────────────
const CREATE_TABLE_SQL = `
  CREATE TABLE IF NOT EXISTS observation (
    id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    parent_span_id TEXT,
    span_kind TEXT NOT NULL,
    name TEXT,
    data TEXT NOT NULL,
    error TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    duration_ms REAL NOT NULL
  )
`;
const INSERT_SQL = `
  INSERT INTO observation
    (id, trace_id, parent_span_id, span_kind, name, data, error, started_at, ended_at, duration_ms)
  VALUES
    (@id, @trace_id, @parent_span_id, @span_kind, @name, @data, @error, @started_at, @ended_at, @duration_ms)
`;
// ── ObservationStore ─────────────────────────────────────────────────────────
class ObservationStore {
    _db;
    constructor(dbPath) {
        this._db = new better_sqlite3_1.default(dbPath);
        this._db.pragma("journal_mode = WAL");
    }
    /** Create the observation table if it does not exist. */
    createTables() {
        this._db.exec(CREATE_TABLE_SQL);
    }
    // ── Write methods ─────────────────────────────────────────────────────
    /** Serialize and insert a single span. */
    save(span) {
        const row = (0, serialization_1.serializeSpan)(span);
        const dataJson = JSON.stringify(row["data"]);
        this._db.prepare(INSERT_SQL).run({
            id: row["id"],
            trace_id: row["trace_id"],
            parent_span_id: row["parent_span_id"],
            span_kind: row["span_kind"],
            name: row["name"],
            data: dataJson,
            error: row["error"],
            started_at: row["started_at"],
            ended_at: row["ended_at"],
            duration_ms: row["duration_ms"],
        });
    }
    /** Batch insert multiple spans (uses a transaction). */
    saveMany(spans) {
        const insert = this._db.prepare(INSERT_SQL);
        const tx = this._db.transaction((items) => {
            for (const span of items) {
                const row = (0, serialization_1.serializeSpan)(span);
                insert.run({
                    id: row["id"],
                    trace_id: row["trace_id"],
                    parent_span_id: row["parent_span_id"],
                    span_kind: row["span_kind"],
                    name: row["name"],
                    data: JSON.stringify(row["data"]),
                    error: row["error"],
                    started_at: row["started_at"],
                    ended_at: row["ended_at"],
                    duration_ms: row["duration_ms"],
                });
            }
        });
        tx(spans);
    }
    // ── Read methods — Trace level ────────────────────────────────────────
    /** Return the trace as a tree of ObservationNode instances. */
    getTrace(traceId) {
        const spans = this.getTraceFlat(traceId);
        if (spans.length === 0)
            return [];
        return (0, tree_1.buildTree)(spans);
    }
    /** Return all spans for a trace as a flat list ordered by started_at. */
    getTraceFlat(traceId) {
        const rows = this._db
            .prepare("SELECT * FROM observation WHERE trace_id = ? ORDER BY started_at ASC")
            .all(traceId);
        return rows.map(rowToDict).map(serialization_1.deserializeSpan);
    }
    // ── Read methods — Eval shortcuts ─────────────────────────────────────
    /**
     * Return the root ObserveSpan (parent_span_id IS NULL).
     * Throws if not found.
     */
    getRoot(traceId) {
        const row = this._db
            .prepare("SELECT * FROM observation " +
            "WHERE trace_id = ? AND parent_span_id IS NULL " +
            "ORDER BY started_at ASC LIMIT 1")
            .get(traceId);
        if (!row) {
            throw new Error(`No root observation found for trace ${traceId}`);
        }
        const span = (0, serialization_1.deserializeSpan)(rowToDict(row));
        if ("operation" in span) {
            throw new Error(`Root span for trace ${traceId} is not an ObserveSpan`);
        }
        return span;
    }
    /** Return the LLM span with the latest ended_at, or null. */
    getLastLlm(traceId) {
        const row = this._db
            .prepare("SELECT * FROM observation " +
            "WHERE trace_id = ? AND span_kind = 'llm' " +
            "ORDER BY ended_at DESC LIMIT 1")
            .get(traceId);
        if (!row)
            return null;
        return (0, serialization_1.deserializeSpan)(rowToDict(row));
    }
    // ── Read methods — Component level ────────────────────────────────────
    /** Return spans matching name, optionally scoped to a trace. */
    getByName(name, traceId) {
        let rows;
        if (traceId !== undefined) {
            rows = this._db
                .prepare("SELECT * FROM observation " +
                "WHERE name = ? AND trace_id = ? ORDER BY started_at ASC")
                .all(name, traceId);
        }
        else {
            rows = this._db
                .prepare("SELECT * FROM observation WHERE name = ? ORDER BY started_at ASC")
                .all(name);
        }
        return rows.map(rowToDict).map(serialization_1.deserializeSpan);
    }
    /** Return spans of a given kind ("observe" or "llm"). */
    getByType(spanKind, traceId) {
        let rows;
        if (traceId !== undefined) {
            rows = this._db
                .prepare("SELECT * FROM observation " +
                "WHERE span_kind = ? AND trace_id = ? ORDER BY started_at ASC")
                .all(spanKind, traceId);
        }
        else {
            rows = this._db
                .prepare("SELECT * FROM observation WHERE span_kind = ? ORDER BY started_at ASC")
                .all(spanKind);
        }
        return rows.map(rowToDict).map(serialization_1.deserializeSpan);
    }
    // ── Read methods — Investigation ──────────────────────────────────────
    /** Return spans with non-null error, optionally scoped to a trace. */
    getErrors(traceId) {
        let rows;
        if (traceId !== undefined) {
            rows = this._db
                .prepare("SELECT * FROM observation " +
                "WHERE error IS NOT NULL AND trace_id = ? ORDER BY started_at ASC")
                .all(traceId);
        }
        else {
            rows = this._db
                .prepare("SELECT * FROM observation WHERE error IS NOT NULL ORDER BY started_at ASC")
                .all();
        }
        return rows.map(rowToDict).map(serialization_1.deserializeSpan);
    }
    /**
     * Return lightweight trace summaries for browsing.
     *
     * Each entry contains `traceId`, `rootName`, `startedAt`, `hasError`,
     * and `observationCount`.
     */
    listTraces(limit = 50, offset = 0) {
        const rows = this._db
            .prepare("SELECT " +
            "  o.trace_id, " +
            "  MIN(CASE WHEN o.parent_span_id IS NULL THEN o.name END) AS root_name, " +
            "  MIN(CASE WHEN o.parent_span_id IS NULL THEN o.started_at END) AS started_at, " +
            "  MAX(CASE WHEN o.error IS NOT NULL THEN 1 ELSE 0 END) AS has_error, " +
            "  COUNT(*) AS observation_count " +
            "FROM observation o " +
            "GROUP BY o.trace_id " +
            "ORDER BY started_at DESC " +
            "LIMIT ? OFFSET ?")
            .all(limit, offset);
        return rows.map((r) => ({
            traceId: r["trace_id"],
            rootName: r["root_name"],
            startedAt: r["started_at"],
            hasError: Boolean(r["has_error"]),
            observationCount: r["observation_count"],
        }));
    }
    /** Close the database connection. */
    close() {
        this._db.close();
    }
}
exports.ObservationStore = ObservationStore;
// ── Helpers ──────────────────────────────────────────────────────────────────
function rowToDict(row) {
    const result = { ...row };
    if (typeof result["data"] === "string") {
        result["data"] = JSON.parse(result["data"]);
    }
    return result;
}
//# sourceMappingURL=store.js.map