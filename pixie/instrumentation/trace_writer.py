"""JSONL trace file writer for wrap events and LLM spans."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

# Module-level trace file writer, set when trace_output is configured.
_trace_writer: TraceFileWriter | None = None


def get_trace_writer() -> TraceFileWriter | None:
    """Return the active TraceFileWriter, or None."""
    return _trace_writer


def set_trace_writer(writer: TraceFileWriter | None) -> None:
    """Set the active TraceFileWriter."""
    global _trace_writer  # noqa: PLW0603
    _trace_writer = writer


def _reset_trace_writer() -> None:
    """Reset the trace writer. **Test-only**."""
    global _trace_writer  # noqa: PLW0603
    _trace_writer = None


class TraceFileWriter:
    """Writes wrap events and LLM spans to a JSONL file.

    Thread-safe: uses a lock for file writes.
    """

    def __init__(self, output_path: str) -> None:
        self._path = Path(output_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        # Truncate the file on init
        self._path.write_text("")

    def write_wrap_event(
        self,
        name: str,
        purpose: str,
        data_serialized: str,
        description: str | None,
        trace_id: str | None = None,
        span_id: str | None = None,
    ) -> None:
        """Write a wrap event as a JSONL line."""
        try:
            data_obj: Any = json.loads(data_serialized)
        except (json.JSONDecodeError, ValueError):
            # Fall back to the raw string if jsonpickle output can't be parsed
            data_obj = data_serialized

        record: dict[str, Any] = {
            "type": "wrap",
            "name": name,
            "purpose": purpose,
            "data": data_obj,
            "description": description,
            "trace_id": trace_id,
            "span_id": span_id,
        }
        self._write_line(record)

    def write_llm_span(self, span_data: dict[str, Any]) -> None:
        """Write an LLM span as a JSONL line."""
        record = {"type": "llm_span", **span_data}
        self._write_line(record)

    def _write_line(self, record: dict[str, Any]) -> None:
        line = json.dumps(record, default=str)
        with self._lock, open(self._path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
