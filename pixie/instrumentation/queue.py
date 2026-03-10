"""_DeliveryQueue — background worker thread for delivering spans to handler."""

from __future__ import annotations

import asyncio
import queue
import threading
from concurrent.futures import Future

from .handler import InstrumentationHandler
from .spans import LLMSpan, ObserveSpan


class _DeliveryQueue:
    """Single queue for both LLMSpan and ObserveSpan.

    A dedicated asyncio event loop runs on a background daemon thread.  The
    queue-worker thread picks up each span and schedules an async dispatch
    coroutine on that loop (fire and forget from the worker's perspective).
    ``queue.task_done()`` is called via a ``Future`` done-callback once the
    coroutine finishes, so ``flush()`` (which calls ``queue.join()``) correctly
    waits for all in-flight async processing to complete.
    """

    def __init__(self, handler: InstrumentationHandler, maxsize: int = 1000) -> None:
        self._handler = handler
        self._queue: queue.Queue[LLMSpan | ObserveSpan] = queue.Queue(maxsize=maxsize)
        self._dropped_count = 0

        # Dedicated event loop running on its own daemon thread.
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._loop.run_forever,
            daemon=True,
            name="pixie-asyncio-loop",
        )
        self._loop_thread.start()

        # Queue-consumer thread: picks items and schedules async tasks.
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
        """Block until all queued items and their async handlers are done."""
        try:
            self._queue.join()
            return True
        except Exception:
            return False

    def _worker(self) -> None:
        """Queue-consumer: fire-and-forget async dispatch for each span."""
        while True:
            item = self._queue.get()
            try:
                future: Future[None] = asyncio.run_coroutine_threadsafe(
                    self._dispatch(item), self._loop
                )
                # task_done() is deferred until the coroutine finishes so
                # that flush() / queue.join() waits for async handlers too.
                future.add_done_callback(lambda _f: self._queue.task_done())
            except Exception:
                # Scheduling failed — mark done immediately to avoid deadlock.
                self._queue.task_done()

    async def _dispatch(self, item: LLMSpan | ObserveSpan) -> None:
        """Async dispatch: route span to the appropriate handler method."""
        try:
            if isinstance(item, LLMSpan):
                await self._handler.on_llm(item)
            elif isinstance(item, ObserveSpan):
                await self._handler.on_observe(item)
        except Exception:
            pass  # Handler exceptions are silently swallowed

    @property
    def dropped_count(self) -> int:
        """Number of spans dropped due to full queue."""
        return self._dropped_count
