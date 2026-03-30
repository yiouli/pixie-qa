"""Tests for pixie.evals.rate_limiter — rate limiting for LLM evaluator calls."""

from __future__ import annotations

import asyncio
import time

import pytest

from pixie.config import PixieConfig
from pixie.evals.rate_limiter import (
    EvalRateLimiter,
    RateLimitConfig,
    configure_rate_limits,
    configure_rate_limits_from_config,
    get_rate_limiter,
)

# ── Config integration tests ──────────────────────────────────────────────


class TestRateLimitConfigIntegration:
    """Tests for config-driven rate limiter setup."""

    def teardown_method(self) -> None:
        configure_rate_limits(None)

    def test_configure_from_pixie_config_creates_limiter(self) -> None:
        configure_rate_limits_from_config(
            PixieConfig(
                rate_limits=RateLimitConfig(rps=10, rpm=100, tps=5000, tpm=200_000)
            )
        )

        limiter = get_rate_limiter()

        assert limiter is not None
        assert limiter.config == RateLimitConfig(rps=10, rpm=100, tps=5000, tpm=200_000)

    def test_configure_from_pixie_config_clears_limiter(self) -> None:
        configure_rate_limits(RateLimitConfig(rps=5))

        configure_rate_limits_from_config(PixieConfig(rate_limits=None))

        assert get_rate_limiter() is None


# ── EvalRateLimiter tests ─────────────────────────────────────────────────


class TestEvalRateLimiter:
    """Tests for EvalRateLimiter."""

    def test_estimate_tokens(self) -> None:
        limiter = EvalRateLimiter(RateLimitConfig())
        assert limiter.estimate_tokens("") == 0
        assert limiter.estimate_tokens("abc") == 1
        assert limiter.estimate_tokens("a" * 30) == 10

    def test_config_property(self) -> None:
        cfg = RateLimitConfig(rps=7)
        limiter = EvalRateLimiter(cfg)
        assert limiter.config is cfg

    @pytest.mark.asyncio
    async def test_acquire_single_request(self) -> None:
        """A single acquire should return immediately."""
        limiter = EvalRateLimiter(RateLimitConfig(rps=10))
        start = time.monotonic()
        await limiter.acquire(estimated_tokens=0)
        elapsed = time.monotonic() - start
        assert elapsed < 0.2

    @pytest.mark.asyncio
    async def test_rps_limits_throughput(self) -> None:
        """With rps=2, third request within 1 second should wait."""
        limiter = EvalRateLimiter(
            RateLimitConfig(rps=2, rpm=1000, tps=1_000_000, tpm=100_000_000)
        )
        # First two requests should be fast
        await limiter.acquire(0)
        await limiter.acquire(0)

        # Third request should be delayed
        start = time.monotonic()
        await limiter.acquire(0)
        elapsed = time.monotonic() - start
        # Should wait at least ~0.05s (one polling interval) before the window slides
        assert elapsed >= 0.04

    @pytest.mark.asyncio
    async def test_concurrent_requests_respect_rps(self) -> None:
        """Concurrent acquires should be serialized by the lock."""
        limiter = EvalRateLimiter(
            RateLimitConfig(rps=3, rpm=1000, tps=1_000_000, tpm=100_000_000)
        )

        results: list[float] = []

        async def acquire_and_record() -> None:
            await limiter.acquire(0)
            results.append(time.monotonic())

        start = time.monotonic()
        await asyncio.gather(*[acquire_and_record() for _ in range(3)])
        # All 3 should succeed (within rps=3 limit)
        assert len(results) == 3
        # Should complete quickly (within 1 second)
        assert time.monotonic() - start < 1.0

    @pytest.mark.asyncio
    async def test_token_rate_limiting(self) -> None:
        """TPS limit should block requests that exceed token budget."""
        limiter = EvalRateLimiter(
            RateLimitConfig(rps=1000, rpm=100_000, tps=100, tpm=100_000_000)
        )
        # First request uses 90 tokens — within budget
        await limiter.acquire(90)

        # Second request with 20 tokens exceeds tps=100
        start = time.monotonic()
        await limiter.acquire(20)
        elapsed = time.monotonic() - start
        # Should have waited for the window to slide
        assert elapsed >= 0.04


# ── Module singleton tests ────────────────────────────────────────────────


class TestModuleSingleton:
    """Tests for configure_rate_limits / get_rate_limiter."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        configure_rate_limits(None)

    def test_default_is_none(self) -> None:
        assert get_rate_limiter() is None

    def test_configure_creates_limiter(self) -> None:
        configure_rate_limits(RateLimitConfig(rps=5))
        limiter = get_rate_limiter()
        assert limiter is not None
        assert limiter.config.rps == 5

    def test_configure_none_clears_limiter(self) -> None:
        configure_rate_limits(RateLimitConfig())
        assert get_rate_limiter() is not None
        configure_rate_limits(None)
        assert get_rate_limiter() is None

    def test_reconfigure_replaces_limiter(self) -> None:
        configure_rate_limits(RateLimitConfig(rps=1))
        first = get_rate_limiter()
        configure_rate_limits(RateLimitConfig(rps=2))
        second = get_rate_limiter()
        assert first is not second
        assert second is not None
        assert second.config.rps == 2

    def teardown_method(self) -> None:
        """Clean up singleton after tests."""
        configure_rate_limits(None)
