"""Shared pytest fixtures for pixie CLI tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def no_browser_open() -> Generator[None, None, None]:
    """Prevent ``webbrowser.open`` from launching a real browser in tests."""
    with patch("webbrowser.open", MagicMock()):
        yield
