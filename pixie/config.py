"""Centralized configuration with env var overrides and sensible defaults.

All environment variables are prefixed with ``PIXIE_``. Values are read at
call time (inside :func:`get_config`), not at import time, so tests can
manipulate ``os.environ`` before calling :func:`get_config`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PixieConfig:
    """Immutable configuration snapshot.

    Attributes:
        db_path: Path to the SQLite database file.
        db_engine: Database engine type (currently only ``"sqlite"``).
    """

    db_path: str = "pixie_observations.db"
    db_engine: str = "sqlite"


def get_config() -> PixieConfig:
    """Read configuration from environment variables with defaults.

    Supported variables:
        - ``PIXIE_DB_PATH`` — overrides :attr:`PixieConfig.db_path`
        - ``PIXIE_DB_ENGINE`` — overrides :attr:`PixieConfig.db_engine`
    """
    return PixieConfig(
        db_path=os.environ.get("PIXIE_DB_PATH", PixieConfig.db_path),
        db_engine=os.environ.get("PIXIE_DB_ENGINE", PixieConfig.db_engine),
    )
