"""Pydantic model for wrap data and JSONL loading utilities.

``WrappedData`` is the canonical representation of a single ``wrap()``
observation — used for trace file entries, dataset ``eval_input`` items,
and in-memory event emission.  All serialization/deserialization of wrap
data goes through this model.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class WrappedData(BaseModel):
    """A single ``wrap()`` observation record.

    Used in three contexts:

    1. **Trace files** — written to JSONL by the trace writer.
    2. **Dataset ``eval_input``** — each dataset item stores its input
       as ``list[WrappedData]`` (JSON-serialized).
    3. **In-memory emission** — created by ``wrap()`` before dispatching.

    Attributes:
        type: Always ``"wrap"`` for wrap events.
        name: The wrap point name (matches ``wrap(name=...)``).
        purpose: One of ``"entry"``, ``"input"``, ``"output"``, ``"state"``.
        data: The observed data value (stored as JSON-compatible value).
        description: Optional human-readable description.
        trace_id: OTel trace ID (if available).
        span_id: OTel span ID (if available).
    """

    type: str = "wrap"
    name: str
    purpose: str
    data: Any
    description: str | None = None
    trace_id: str | None = None
    span_id: str | None = None


# Backward-compatible alias
WrapLogEntry = WrappedData


def parse_wrapped_data_list(raw: Any) -> list[WrappedData]:
    """Parse a JSON value into a list of :class:`WrappedData`.

    Validates that *raw* is a list of dicts, each with at least
    ``purpose`` and ``name`` keys, and returns validated models.

    Args:
        raw: A JSON-compatible value (typically from ``eval_input``).

    Returns:
        List of validated :class:`WrappedData` objects.

    Raises:
        ValueError: If *raw* is not a list or any item is malformed.
    """
    if not isinstance(raw, list):
        raise ValueError(
            f"Expected eval_input to be a list of WrappedData objects, "
            f"got {type(raw).__name__}. "
            f"Use 'pixie trace filter --purpose entry,input' output as the template."
        )
    result: list[WrappedData] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(
                f"eval_input[{i}]: expected a WrappedData object (dict), "
                f"got {type(item).__name__}."
            )
        if "purpose" not in item or "name" not in item:
            raise ValueError(
                f"eval_input[{i}]: missing required 'purpose' and/or 'name' fields. "
                f"Each eval_input item must be a WrappedData object with "
                f"type, name, purpose, and data fields."
            )
        result.append(WrappedData.model_validate(item))
    return result


def load_wrap_log_entries(jsonl_path: str | Path) -> list[WrappedData]:
    """Load all wrap log entries from a JSONL file.

    Skips non-wrap lines (e.g. ``type=llm_span``) and malformed lines.

    Args:
        jsonl_path: Path to a JSONL trace file.

    Returns:
        List of :class:`WrappedData` objects.
    """
    entries: list[WrappedData] = []
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
                entries.append(WrappedData.model_validate(record))
            except Exception:
                continue
    return entries


def filter_by_purpose(
    entries: list[WrappedData],
    purposes: set[str],
) -> list[WrappedData]:
    """Filter wrap log entries by purpose.

    Args:
        entries: List of wrap data entries.
        purposes: Set of purpose values to include.

    Returns:
        Filtered list.
    """
    return [e for e in entries if e.purpose in purposes]
