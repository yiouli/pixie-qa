"""Piccolo engine configuration for the observation store."""

from __future__ import annotations

from piccolo.engine.sqlite import SQLiteEngine

from pixie.config import get_config

_config = get_config()
DB = SQLiteEngine(path=_config.db_path)
