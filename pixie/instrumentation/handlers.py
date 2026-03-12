"""Pre-made span handlers for common persistence patterns.

Provides :class:`StorageHandler` — an async handler that writes spans to an
:class:`~pixie.storage.store.ObservationStore` — and the :func:`enable_storage`
convenience function for zero-config setup.
"""

from __future__ import annotations

import contextlib

from pixie.config import get_config
from pixie.instrumentation.handler import InstrumentationHandler
from pixie.instrumentation.observation import add_handler, init
from pixie.instrumentation.spans import LLMSpan, ObserveSpan
from pixie.storage.store import ObservationStore


class StorageHandler(InstrumentationHandler):
    """Span handler that persists completed spans to an :class:`ObservationStore`.

    Both ``on_llm`` and ``on_observe`` are async coroutines so
    ``store.save()`` is awaited directly inside the asyncio event loop
    managed by ``_DeliveryQueue``. Exceptions are silently swallowed to
    avoid crashing the delivery pipeline.
    """

    def __init__(self, store: ObservationStore) -> None:
        self.store = store

    async def on_llm(self, span: LLMSpan) -> None:
        """Persist an LLM span to the observation store."""
        with contextlib.suppress(Exception):
            await self.store.save(span)

    async def on_observe(self, span: ObserveSpan) -> None:
        """Persist an observe span to the observation store."""
        with contextlib.suppress(Exception):
            await self.store.save(span)


_storage_handler: StorageHandler | None = None


async def _setup_storage() -> StorageHandler:
    """Internal: create store, ensure tables exist, return handler."""
    import os

    config = get_config()
    from piccolo.engine.sqlite import SQLiteEngine

    # Ensure the root directory exists so the DB file can be created.
    db_dir = os.path.dirname(config.db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    engine = SQLiteEngine(path=config.db_path)
    store = ObservationStore(engine=engine)
    await store.create_tables()
    return StorageHandler(store)


def enable_storage() -> StorageHandler:
    """Set up Piccolo storage with default config and register the handler.

    Creates the ``pixie_qa`` root directory and observation table if they
    don't exist.  Truly idempotent — calling twice returns the same
    handler without duplicating registrations, even from different threads
    or from within an async context.

    Returns:
        The :class:`StorageHandler` for optional manual control.
    """
    global _storage_handler  # noqa: PLW0603
    if _storage_handler is not None:
        return _storage_handler

    import asyncio

    init()

    # Support being called both from sync (no running loop) and async
    # contexts (running loop already present).
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            handler = pool.submit(asyncio.run, _setup_storage()).result()
    else:
        handler = asyncio.run(_setup_storage())

    add_handler(handler)
    _storage_handler = handler
    return handler


def _reset_storage_handler() -> None:
    """Reset the module-level handler. **Test-only** — not part of the public API."""
    global _storage_handler  # noqa: PLW0603
    _storage_handler = None
