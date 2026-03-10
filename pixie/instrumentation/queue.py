"""_DeliveryQueue — background worker thread for delivering spans to handler."""

from __future__ import annotations

import queue
import threading

from .handler import InstrumentationHandler
from .spans import LLMSpan, ObserveSpan


class _DeliveryQueue:
    """Single queue for both LLMSpan and ObserveSpan.

    Handler methods are dispatched by type on a background daemon thread.
    """

    def __init__(self, handler: InstrumentationHandler, maxsize: int = 1000) -> None:
        self._handler = handler
        self._queue: queue.Queue[LLMSpan | ObserveSpan] = queue.Queue(maxsize=maxsize)
        self._dropped_count = 0
        self._thread = threading.Thread(
            target=self._worker, daemon=True, name="pixie-delivery-worker"
        )
        self._thread.start()

    def submit(self, item: LLMSpan | ObserveSpan) -> None:
        """Submit a span for delivery. Drops silently on full queue."""
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            self._dropped_count += 1

    def flush(self, timeout_seconds: float = 5.0) -> bool:
        """Block until all queued items are processed."""
        try:
            self._queue.join()
            return True
        except Exception:
            return False

    def _worker(self) -> None:
        """Background worker that processes spans and dispatches to handler."""
        while True:
            item = self._queue.get()
            try:
                if isinstance(item, LLMSpan):
                    self._handler.on_llm(item)
                elif isinstance(item, ObserveSpan):
                    self._handler.on_observe(item)
            except Exception:
                pass  # Handler exceptions are silently swallowed
            finally:
                self._queue.task_done()

    @property
    def dropped_count(self) -> int:
        """Number of spans dropped due to full queue."""
        return self._dropped_count
