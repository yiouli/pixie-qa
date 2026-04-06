"""Pydantic model for wrap log entries and JSONL loading utilities.

``WrapLogEntry`` is the typed representation of a single ``wrap()`` event
as recorded in a JSONL trace file.  Multiple places in the codebase load
these objects — the ``pixie trace filter`` CLI, the dataset loader, and
the verification scripts — so they share this single model.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict


class WrapLogEntry(BaseModel):
    """A single wrap() event as logged to a JSONL trace file.

    Attributes:
        type: Always ``"wrap"`` for wrap events.
        name: The wrap point name (matches ``wrap(name=...)``).
        purpose: One of ``"entry"``, ``"input"``, ``"output"``, ``"state"``.
        data: The serialized data (jsonpickle string).
        description: Optional human-readable description.
        trace_id: OTel trace ID (if available).
        span_id: OTel span ID (if available).
    """

    model_config = ConfigDict(frozen=True)

    type: str = "wrap"
    name: str
    purpose: str
    data: Any  # jsonpickle-encoded value (stored as JSON object in JSONL)
    description: str | None = None
    trace_id: str | None = None
    span_id: str | None = None


def load_wrap_log_entries(jsonl_path: str | Path) -> list[WrapLogEntry]:
    """Load all wrap log entries from a JSONL file.

    Skips non-wrap lines (e.g. ``type=llm_span``) and malformed lines.

    Args:
        jsonl_path: Path to a JSONL trace file.

    Returns:
        List of :class:`WrapLogEntry` objects.
    """
    entries: list[WrapLogEntry] = []
    path = Path(jsonl_path)
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("type") != "wrap":
                continue
            try:
                entries.append(WrapLogEntry.model_validate(record))
            except Exception:
                continue
    return entries


def filter_by_purpose(
    entries: list[WrapLogEntry],
    purposes: set[str],
) -> list[WrapLogEntry]:
    """Filter wrap log entries by purpose.

    Args:
        entries: List of wrap log entries.
        purposes: Set of purpose values to include.

    Returns:
        Filtered list.
    """
    return [e for e in entries if e.purpose in purposes]
