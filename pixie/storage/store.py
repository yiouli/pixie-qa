"""ObservationStore — async persistence and query API for observation spans."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from piccolo.engine.sqlite import SQLiteEngine

from pixie.instrumentation.spans import LLMSpan, ObserveSpan
from pixie.storage.serialization import deserialize_span, serialize_span
from pixie.storage.tables import Observation
from pixie.storage.tree import ObservationNode, build_tree


class ObservationStore:
    """Async store for persisting and querying observation spans.

    Backed by a Piccolo ORM SQLite table. Call :meth:`create_tables` once
    before first use to ensure the schema exists.
    """

    def __init__(self, engine: SQLiteEngine | None = None) -> None:
        if engine is not None:
            Observation._meta._db = engine  # type: ignore[unused-ignore,attr-defined]
        self._engine = engine

    async def create_tables(self) -> None:
        """Create the observation table if it does not exist."""
        await Observation.create_table(if_not_exists=True)

    # ── Write methods ─────────────────────────────────────────────────────

    async def save(self, span: ObserveSpan | LLMSpan) -> None:
        """Serialize and insert a single span."""
        row = serialize_span(span)
        data_json = json.dumps(row["data"], default=str)
        await Observation.raw(
            "INSERT INTO observation "
            "(id, trace_id, parent_span_id, span_kind, name, data, error, "
            "started_at, ended_at, duration_ms) "
            "VALUES ({}, {}, {}, {}, {}, {}, {}, {}, {}, {})",
            row["id"],
            row["trace_id"],
            row["parent_span_id"],
            row["span_kind"],
            row["name"],
            data_json,
            row["error"],
            (
                row["started_at"].isoformat()
                if isinstance(row["started_at"], datetime)
                else row["started_at"]
            ),
            (
                row["ended_at"].isoformat()
                if isinstance(row["ended_at"], datetime)
                else row["ended_at"]
            ),
            row["duration_ms"],
        )

    async def save_many(self, spans: list[ObserveSpan | LLMSpan]) -> None:
        """Batch insert multiple spans."""
        for span in spans:
            await self.save(span)

    # ── Read methods — Trace level ────────────────────────────────────────

    async def get_trace(self, trace_id: str) -> list[ObservationNode]:
        """Return the trace as a tree of ``ObservationNode`` instances.

        Empty list if no observations found for *trace_id*.
        """
        spans = await self.get_trace_flat(trace_id)
        if not spans:
            return []
        return build_tree(spans)

    async def get_trace_flat(self, trace_id: str) -> list[ObserveSpan | LLMSpan]:
        """Return all spans for a trace as a flat list ordered by ``started_at``."""
        rows = await Observation.raw(
            "SELECT * FROM observation WHERE trace_id = {} ORDER BY started_at ASC",
            trace_id,
        )
        return [deserialize_span(_row_to_dict(r)) for r in rows]

    # ── Read methods — Eval shortcuts ─────────────────────────────────────

    async def get_root(self, trace_id: str) -> ObserveSpan:
        """Return the root ``ObserveSpan`` (``parent_span_id IS NULL``).

        Raises ``ValueError`` if not found. If multiple roots, returns the
        earliest by ``started_at``.
        """
        rows = await Observation.raw(
            "SELECT * FROM observation "
            "WHERE trace_id = {} AND parent_span_id IS NULL "
            "ORDER BY started_at ASC LIMIT 1",
            trace_id,
        )
        if not rows:
            raise ValueError(f"No root observation found for trace {trace_id}")
        span = deserialize_span(_row_to_dict(rows[0]))
        if not isinstance(span, ObserveSpan):
            raise ValueError(f"Root span for trace {trace_id} is not an ObserveSpan")
        return span

    async def get_last_llm(self, trace_id: str) -> LLMSpan | None:
        """Return the LLM span with the latest ``ended_at``, or ``None``."""
        rows = await Observation.raw(
            "SELECT * FROM observation "
            "WHERE trace_id = {} AND span_kind = 'llm' "
            "ORDER BY ended_at DESC LIMIT 1",
            trace_id,
        )
        if not rows:
            return None
        span = deserialize_span(_row_to_dict(rows[0]))
        assert isinstance(span, LLMSpan)
        return span

    # ── Read methods — Component level ────────────────────────────────────

    async def get_by_name(
        self,
        name: str,
        trace_id: str | None = None,
    ) -> list[ObserveSpan | LLMSpan]:
        """Return spans matching *name*, optionally scoped to a trace."""
        if trace_id is not None:
            rows = await Observation.raw(
                "SELECT * FROM observation "
                "WHERE name = {} AND trace_id = {} ORDER BY started_at ASC",
                name,
                trace_id,
            )
        else:
            rows = await Observation.raw(
                "SELECT * FROM observation WHERE name = {} ORDER BY started_at ASC",
                name,
            )
        return [deserialize_span(_row_to_dict(r)) for r in rows]

    async def get_by_type(
        self,
        span_kind: str,
        trace_id: str | None = None,
    ) -> list[ObserveSpan | LLMSpan]:
        """Return spans of *span_kind* (``"observe"`` or ``"llm"``)."""
        if trace_id is not None:
            rows = await Observation.raw(
                "SELECT * FROM observation "
                "WHERE span_kind = {} AND trace_id = {} ORDER BY started_at ASC",
                span_kind,
                trace_id,
            )
        else:
            rows = await Observation.raw(
                "SELECT * FROM observation "
                "WHERE span_kind = {} ORDER BY started_at ASC",
                span_kind,
            )
        return [deserialize_span(_row_to_dict(r)) for r in rows]

    # ── Read methods — Investigation ──────────────────────────────────────

    async def get_errors(
        self,
        trace_id: str | None = None,
    ) -> list[ObserveSpan | LLMSpan]:
        """Return spans with non-null error, optionally scoped to a trace."""
        if trace_id is not None:
            rows = await Observation.raw(
                "SELECT * FROM observation "
                "WHERE error IS NOT NULL AND trace_id = {} ORDER BY started_at ASC",
                trace_id,
            )
        else:
            rows = await Observation.raw(
                "SELECT * FROM observation "
                "WHERE error IS NOT NULL ORDER BY started_at ASC",
            )
        return [deserialize_span(_row_to_dict(r)) for r in rows]

    async def list_traces(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Return lightweight trace summaries for browsing.

        Each dict contains ``trace_id``, ``root_name``, ``started_at``,
        ``has_error``, and ``observation_count``. Ordered most recent first.
        """
        rows = await Observation.raw(
            "SELECT "
            "  o.trace_id, "
            "  MIN(CASE WHEN o.parent_span_id IS NULL THEN o.name END) AS root_name, "
            "  MIN(CASE WHEN o.parent_span_id IS NULL THEN o.started_at END) "
            "    AS started_at, "
            "  MAX(CASE WHEN o.error IS NOT NULL THEN 1 ELSE 0 END) AS has_error, "
            "  COUNT(*) AS observation_count "
            "FROM observation o "
            "GROUP BY o.trace_id "
            "ORDER BY started_at DESC "
            "LIMIT {} OFFSET {}",
            limit,
            offset,
        )
        result: list[dict[str, Any]] = []
        for r in rows:
            row_dict = dict(r) if not isinstance(r, dict) else r
            result.append(
                {
                    "trace_id": row_dict["trace_id"],
                    "root_name": row_dict["root_name"],
                    "started_at": row_dict["started_at"],
                    "has_error": bool(row_dict["has_error"]),
                    "observation_count": row_dict["observation_count"],
                }
            )
        return result


def _row_to_dict(row: Any) -> dict[str, Any]:
    """Convert a Piccolo raw query row to a plain dict with parsed JSON data."""
    row_dict: dict[str, Any] = dict(row) if not isinstance(row, dict) else row
    # Piccolo SQLite returns JSON columns as strings
    if isinstance(row_dict.get("data"), str):
        row_dict["data"] = json.loads(row_dict["data"])
    return row_dict
