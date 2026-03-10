"""Piccolo ORM table definition for the observation store."""

from __future__ import annotations

from piccolo.columns.column_types import JSONB, Real, Text, Timestamptz, Varchar
from piccolo.table import Table


class Observation(Table, tablename="observation"):
    """Single table for persisting both ObserveSpan and LLMSpan records."""

    id = Varchar(length=16, primary_key=True)
    trace_id = Varchar(length=64, index=True)
    parent_span_id = Varchar(length=16, null=True, default=None)
    span_kind = Varchar(length=16)
    name = Varchar(length=256, null=True, index=True)
    data = JSONB()
    error = Text(null=True, default=None)
    started_at = Timestamptz()
    ended_at = Timestamptz()
    duration_ms = Real()
