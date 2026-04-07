"""OTel log-record processors for ``wrap()`` events.

``wrap()`` emits every observation as an OTel log record via its module-level
``LoggerProvider``.  Consumers register a ``LogRecordProcessor`` on that
provider to react to wrap events.

Two processors are shipped:

* :class:`TraceLogProcessor` — writes each event body as a JSON line to a file.
  Also exposes :meth:`write_line` for non-wrap records (kwargs, LLM spans).
* :class:`EvalCaptureLogProcessor` — appends ``purpose="output"`` /
  ``purpose="state"`` event bodies to the ``eval_output`` context variable
  so the test runner can collect them into ``Evaluable.eval_output``.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from opentelemetry.sdk._logs import LogRecordProcessor, ReadWriteLogRecord

from pixie.instrumentation.wrap_registry import get_eval_output

# Module-level trace log processor reference, set by the trace command.
_trace_log_processor: TraceLogProcessor | None = None

# Guard: has an EvalCaptureLogProcessor been registered?
_eval_capture_registered = False


def get_trace_log_processor() -> TraceLogProcessor | None:
    """Return the active :class:`TraceLogProcessor`, or ``None``."""
    return _trace_log_processor


def set_trace_log_processor(processor: TraceLogProcessor | None) -> None:
    """Set the active :class:`TraceLogProcessor`."""
    global _trace_log_processor  # noqa: PLW0603
    _trace_log_processor = processor


def ensure_eval_capture_registered() -> None:
    """Register a single :class:`EvalCaptureLogProcessor` on the wrap logger.

    Safe to call multiple times — only the first call has an effect.
    """
    global _eval_capture_registered  # noqa: PLW0603
    if _eval_capture_registered:
        return
    from pixie.instrumentation.wrap import logger_provider

    logger_provider.add_log_record_processor(EvalCaptureLogProcessor())
    _eval_capture_registered = True


class TraceLogProcessor(LogRecordProcessor):
    """Write wrap event bodies as JSON lines to a file.

    Args:
        output_path: Path to the JSONL trace file.  Parent directories
            are created if missing; the file is truncated on init.
    """

    def __init__(self, output_path: str) -> None:
        self._path = Path(output_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._path.write_text("")

    def on_emit(self, log_record: ReadWriteLogRecord) -> None:  # noqa: D102
        body = log_record.log_record.body
        if not isinstance(body, dict):
            return
        line = json.dumps(body, default=str)
        with self._lock, open(self._path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def shutdown(self) -> None:  # noqa: D102
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:  # noqa: D102
        return True

    def write_line(self, record: dict[str, Any]) -> None:
        """Write an arbitrary JSON record (e.g. kwargs, llm_span)."""
        line = json.dumps(record, default=str)
        with self._lock, open(self._path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


class EvalCaptureLogProcessor(LogRecordProcessor):
    """Append wrap event bodies to the ``eval_output`` context variable.

    Only events with ``purpose="output"`` or ``purpose="state"`` are
    captured.  The processor is a no-op when ``eval_output`` has not been
    initialised (i.e. outside of an eval run).
    """

    def on_emit(self, log_record: ReadWriteLogRecord) -> None:  # noqa: D102
        body = log_record.log_record.body
        if not isinstance(body, dict):
            return

        purpose = body.get("purpose")
        if purpose not in ("output", "state"):
            return

        eval_output = get_eval_output()
        if eval_output is not None:
            eval_output.append(body)

    def shutdown(self) -> None:  # noqa: D102
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:  # noqa: D102
        return True
