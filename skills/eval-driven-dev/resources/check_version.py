#!/usr/bin/env python3
"""Check whether the eval-driven-dev skill and pixie-qa package need updating.

Prints one of:
  "SKILL upgrade available"
  "Package upgrade available"
  "SKILL and Package upgrade available"
  "All up to date"

Exit codes:
  0 — everything is up to date (or status could not be determined)
  1 — at least one component needs an upgrade
"""

from __future__ import annotations

import importlib.metadata
import json
import re
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

# ── Constants ────────────────────────────────────────────────────────────────

SKILL_URL = (
    "https://raw.githubusercontent.com/yiouli/pixie-qa/"
    "main/skills/eval-driven-dev/SKILL.md"
)
PYPI_URL = "https://pypi.org/pypi/pixie-qa/json"

# ── Helpers ──────────────────────────────────────────────────────────────────

_RE_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_RE_VERSION = re.compile(r"^\s+version:\s*(\S+)$", re.MULTILINE)


def _parse_version(text: str) -> str:
    """Extract metadata.version from SKILL.md YAML frontmatter."""
    match = _RE_FRONTMATTER.search(text)
    frontmatter = match.group(1) if match else text
    m = _RE_VERSION.search(frontmatter)
    return m.group(1).strip() if m else "0.0.0"


def _normalise_version(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for part in version.strip().split("."):
        try:
            parts.append(int(part))
        except ValueError:
            break
    return tuple(parts)


# ── Skill check ──────────────────────────────────────────────────────────────


def _skill_needs_upgrade() -> bool:
    """Return True if a newer version of the skill is available on GitHub."""
    resource_dir = Path(__file__).resolve().parent
    skill_path = resource_dir.parent / "SKILL.md"
    if not skill_path.exists():
        # SKILL.md is not on disk (e.g. prompt-based agents); skip check.
        return False
    local_text = skill_path.read_text(encoding="utf-8")
    local_version = _parse_version(local_text)
    try:
        with urlopen(SKILL_URL, timeout=10) as resp:
            remote_version = _parse_version(resp.read().decode("utf-8"))
    except (OSError, URLError):
        return False
    return _normalise_version(remote_version) > _normalise_version(local_version)


# ── Package check ─────────────────────────────────────────────────────────────


def _is_local_install(dist: importlib.metadata.Distribution) -> bool:
    """Return True if pixie-qa was installed from a local path rather than PyPI."""
    try:
        text = dist.read_text("direct_url.json")
        if text:
            url: str = json.loads(text).get("url", "")
            return url.startswith("file://")
    except Exception:
        pass
    return False


def _package_needs_upgrade() -> bool:
    """Return True if pixie-qa is missing or a newer version is on PyPI."""
    try:
        dist = importlib.metadata.distribution("pixie-qa")
    except importlib.metadata.PackageNotFoundError:
        return True
    if _is_local_install(dist):
        return False
    installed: str = dist.metadata["Version"]
    try:
        with urlopen(PYPI_URL, timeout=10) as resp:
            latest: str = json.loads(resp.read().decode("utf-8"))["info"]["version"]
    except (OSError, URLError, KeyError, ValueError):
        return False
    return _normalise_version(latest) > _normalise_version(installed)


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> int:
    skill = _skill_needs_upgrade()
    package = _package_needs_upgrade()
    if skill and package:
        print("SKILL and Package upgrade available")
    elif skill:
        print("SKILL upgrade available")
    elif package:
        print("Package upgrade available")
    else:
        print("All up to date")
    return 1 if (skill or package) else 0


if __name__ == "__main__":
    raise SystemExit(main())
