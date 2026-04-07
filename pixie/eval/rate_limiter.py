"""Central rate limiter for LLM evaluator calls.

Controls throughput using configurable RPS, RPM, TPS, and TPM limits.
Uses asyncio primitives (Semaphore + sliding window) so it integrates
naturally with the async evaluation pipeline.

Usage::

    from pixie.eval.rate_limiter import configure_rate_limits_from_config

    configure_rate_limits_from_config()

The module exposes a singleton via ``get_rate_limiter()``; when no
configuration has been applied the function returns ``None`` and
evaluator calls proceed without throttling.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque

from pixie.config import PixieConfig, RateLimitConfig, get_config

__all__ = [
    "EvalRateLimiter",
    "RateLimitConfig",
    "configure_rate_limits",
    "configure_rate_limits_from_config",
    "get_rate_limiter",
]


class EvalRateLimiter:
    """Central rate limiter for LLM evaluator calls.

    Enforces both request-count and token-count limits using sliding
    windows.  All public methods are async and safe to call from
    concurrent ``asyncio.gather`` tasks.
    """

    def __init__(self, config: RateLimitConfig) -> None:
        self._config = config
        self._lock = asyncio.Lock()

        # Sliding-window records: (timestamp, token_count)
        self._second_window: deque[tuple[float, int]] = deque()
        self._minute_window: deque[tuple[float, int]] = deque()

    @property
    def config(self) -> RateLimitConfig:
        """Return the current configuration."""
        return self._config

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count using ``len(text) // 3`` approximation."""
        return len(text) // 3

    async def acquire(self, estimated_tokens: int = 0) -> None:
        """Wait until the request can proceed within rate limits.

        Blocks (with a short polling interval) until *all* four
        constraints (RPS, RPM, TPS, TPM) are satisfied, then records
        the request in the sliding windows.
        """
        while True:
            async with self._lock:
                now = time.monotonic()
                self._evict(now)

                if self._can_proceed(now, estimated_tokens):
                    self._record(now, estimated_tokens)
                    return

            # Yield control and retry after a short wait
            await asyncio.sleep(0.05)

    # ── internals ────────────────────────────────────────────────────

    def _evict(self, now: float) -> None:
        """Remove entries older than their respective windows."""
        while self._second_window and now - self._second_window[0][0] >= 1.0:
            self._second_window.popleft()
        while self._minute_window and now - self._minute_window[0][0] >= 60.0:
            self._minute_window.popleft()

    def _can_proceed(self, now: float, tokens: int) -> bool:
        """Return ``True`` if all rate-limit constraints are satisfied."""
        sec_count = len(self._second_window)
        sec_tokens = sum(t for _, t in self._second_window)
        min_count = len(self._minute_window)
        min_tokens = sum(t for _, t in self._minute_window)

        if sec_count >= self._config.rps:
            return False
        if min_count >= self._config.rpm:
            return False
        if sec_tokens + tokens > self._config.tps:
            return False
        return min_tokens + tokens <= self._config.tpm

    def _record(self, now: float, tokens: int) -> None:
        """Record a request in both sliding windows."""
        self._second_window.append((now, tokens))
        self._minute_window.append((now, tokens))


# ── module-level singleton ───────────────────────────────────────────────

_rate_limiter: EvalRateLimiter | None = None
_rate_limiter_initialized = False


def configure_rate_limits(config: RateLimitConfig | None = None) -> None:
    """Set (or clear) the global rate limiter for evaluator calls.

    Pass a ``RateLimitConfig`` to enable rate limiting, or ``None`` to
    disable it.

    Args:
        config: The rate-limit configuration.  Passing ``None`` removes
            any previously configured limiter.
    """
    global _rate_limiter, _rate_limiter_initialized  # noqa: PLW0603
    _rate_limiter = None if config is None else EvalRateLimiter(config)
    _rate_limiter_initialized = True


def configure_rate_limits_from_config(config: PixieConfig | None = None) -> None:
    """Apply the central Pixie config to the module-level rate limiter."""
    resolved_config = get_config() if config is None else config
    configure_rate_limits(resolved_config.rate_limits)


def get_rate_limiter() -> EvalRateLimiter | None:
    """Return the active rate limiter, auto-loading it from Pixie config once."""
    if not _rate_limiter_initialized:
        configure_rate_limits_from_config()
    return _rate_limiter
