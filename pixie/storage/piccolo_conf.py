"""Piccolo engine configuration for the observation store."""

from __future__ import annotations

import os

from piccolo.engine.sqlite import SQLiteEngine

DB = SQLiteEngine(path=os.environ.get("PIXIE_DB_PATH", "pixie_observations.db"))
