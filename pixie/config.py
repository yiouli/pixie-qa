"""Centralized configuration with env var overrides and sensible defaults.

All environment variables are prefixed with ``PIXIE_``. Values are read at
call time (inside :func:`get_config`), not at import time, so tests can
manipulate ``os.environ`` before calling :func:`get_config`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

#: Default root directory for all pixie-generated artefacts.
DEFAULT_ROOT = "pixie_qa"


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
    """

    root: str = DEFAULT_ROOT
    db_path: str = os.path.join(DEFAULT_ROOT, "observations.db")
    db_engine: str = "sqlite"
    dataset_dir: str = os.path.join(DEFAULT_ROOT, "datasets")


def get_config() -> PixieConfig:
    """Read configuration from environment variables with defaults.

    Supported variables:
        - ``PIXIE_ROOT`` — overrides :attr:`PixieConfig.root` (the base
          directory for all artefacts)
        - ``PIXIE_DB_PATH`` — overrides :attr:`PixieConfig.db_path`
        - ``PIXIE_DB_ENGINE`` — overrides :attr:`PixieConfig.db_engine`
        - ``PIXIE_DATASET_DIR`` — overrides :attr:`PixieConfig.dataset_dir`
    """
    root = os.environ.get("PIXIE_ROOT", PixieConfig.root)
    return PixieConfig(
        root=root,
        db_path=os.environ.get("PIXIE_DB_PATH", os.path.join(root, "observations.db")),
        db_engine=os.environ.get("PIXIE_DB_ENGINE", PixieConfig.db_engine),
        dataset_dir=os.environ.get("PIXIE_DATASET_DIR", os.path.join(root, "datasets")),
    )
