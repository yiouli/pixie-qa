"""Centralized configuration with env var and ``.env`` overrides.

All environment variables are prefixed with ``PIXIE_``. ``get_config()`` loads
the nearest ``.env`` from the current working directory at call time, while
preserving any variables already present in ``os.environ``. Values are still
resolved at call time rather than import time so tests can safely manipulate
the process environment before calling :func:`get_config`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import find_dotenv, load_dotenv

#: Default root directory for all pixie-generated artefacts.
DEFAULT_ROOT = "pixie_qa"
DEFAULT_RATE_LIMIT_RPS = 4.0
DEFAULT_RATE_LIMIT_RPM = 50.0
DEFAULT_RATE_LIMIT_TPS = 10_000.0
DEFAULT_RATE_LIMIT_TPM = 500_000.0

_TRUE_ENV_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class RateLimitConfig:
    """Configuration for evaluator rate limiting.

    Attributes:
        rps: Max requests per second.
        rpm: Max requests per minute.
        tps: Max tokens per second.
        tpm: Max tokens per minute.
    """

    rps: float = DEFAULT_RATE_LIMIT_RPS
    rpm: float = DEFAULT_RATE_LIMIT_RPM
    tps: float = DEFAULT_RATE_LIMIT_TPS
    tpm: float = DEFAULT_RATE_LIMIT_TPM


@dataclass(frozen=True)
class PixieConfig:
    """Immutable configuration snapshot.

    All paths default to subdirectories / files within a single ``pixie_qa``
    project folder so that observations, datasets, tests, scripts and notes
    live in one predictable location.

    Attributes:
        root: Root directory for all pixie artefacts.
        db_path: Path to the SQLite database file.
        db_engine: Database engine type (currently only ``"sqlite"``).
        dataset_dir: Directory for dataset JSON files.
        rate_limits: Optional evaluator rate limits loaded from ``PIXIE_RATE_LIMIT_*``.
    """

    root: str = DEFAULT_ROOT
    db_path: str = os.path.join(DEFAULT_ROOT, "observations.db")
    db_engine: str = "sqlite"
    dataset_dir: str = os.path.join(DEFAULT_ROOT, "datasets")
    rate_limits: RateLimitConfig | None = None
    trace_output: str | None = None  # path for JSONL trace file
    tracing_enabled: bool = False    # whether tracing is active


def _is_truthy_env(value: str) -> bool:
    """Return ``True`` when an env var value enables a boolean flag."""
    return value.strip().lower() in _TRUE_ENV_VALUES


def _get_float_env(name: str, default: float) -> float:
    """Return a float env var value or a provided default."""
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return float(raw_value)


def _get_rate_limit_config() -> RateLimitConfig | None:
    """Build a rate-limit config when it is enabled through env vars."""
    enabled_value = os.environ.get("PIXIE_RATE_LIMIT_ENABLED")
    has_rate_limit_overrides = any(
        os.environ.get(name) is not None
        for name in (
            "PIXIE_RATE_LIMIT_RPS",
            "PIXIE_RATE_LIMIT_RPM",
            "PIXIE_RATE_LIMIT_TPS",
            "PIXIE_RATE_LIMIT_TPM",
        )
    )

    if enabled_value is not None and not _is_truthy_env(enabled_value):
        return None
    if enabled_value is None and not has_rate_limit_overrides:
        return None

    return RateLimitConfig(
        rps=_get_float_env("PIXIE_RATE_LIMIT_RPS", RateLimitConfig.rps),
        rpm=_get_float_env("PIXIE_RATE_LIMIT_RPM", RateLimitConfig.rpm),
        tps=_get_float_env("PIXIE_RATE_LIMIT_TPS", RateLimitConfig.tps),
        tpm=_get_float_env("PIXIE_RATE_LIMIT_TPM", RateLimitConfig.tpm),
    )


def get_config() -> PixieConfig:
    """Read configuration from environment variables with defaults.

    Supported variables:
        - ``PIXIE_ROOT`` — overrides :attr:`PixieConfig.root` (the base
          directory for all artefacts)
        - ``PIXIE_DB_PATH`` — overrides :attr:`PixieConfig.db_path`
        - ``PIXIE_DB_ENGINE`` — overrides :attr:`PixieConfig.db_engine`
        - ``PIXIE_DATASET_DIR`` — overrides :attr:`PixieConfig.dataset_dir`
        - ``PIXIE_RATE_LIMIT_ENABLED`` — enables evaluator rate limiting
        - ``PIXIE_RATE_LIMIT_RPS`` — overrides :attr:`RateLimitConfig.rps`
        - ``PIXIE_RATE_LIMIT_RPM`` — overrides :attr:`RateLimitConfig.rpm`
        - ``PIXIE_RATE_LIMIT_TPS`` — overrides :attr:`RateLimitConfig.tps`
        - ``PIXIE_RATE_LIMIT_TPM`` — overrides :attr:`RateLimitConfig.tpm`
        - ``PIXIE_TRACE_OUTPUT`` — path for JSONL trace output file;
          overrides :attr:`PixieConfig.trace_output`
        - ``PIXIE_TRACING`` — set to ``1``/``true``/``yes``/``on`` to enable
          tracing mode; overrides :attr:`PixieConfig.tracing_enabled`
    """
    load_dotenv(find_dotenv(usecwd=True), override=False)

    root = os.environ.get("PIXIE_ROOT", PixieConfig.root)
    return PixieConfig(
        root=root,
        db_path=os.environ.get("PIXIE_DB_PATH", os.path.join(root, "observations.db")),
        db_engine=os.environ.get("PIXIE_DB_ENGINE", PixieConfig.db_engine),
        dataset_dir=os.environ.get("PIXIE_DATASET_DIR", os.path.join(root, "datasets")),
        rate_limits=_get_rate_limit_config(),
        trace_output=os.environ.get("PIXIE_TRACE_OUTPUT"),
        tracing_enabled=_is_truthy_env(os.environ.get("PIXIE_TRACING", "")),
    )
