#!/usr/bin/env python3
"""Check whether the qa-eval skill is outdated and update it if needed."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

SKILL_REPO = "/yiouli/pixie-qa/"
SKILL_URL = f"https://raw.githubusercontent.com{SKILL_REPO}main/skills/qa-eval/SKILL.md"

_RE_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_RE_NAME = re.compile(r"^name:\s*(.+)$", re.MULTILINE)
_RE_VERSION = re.compile(r"^\s+version:\s*(\S+)$", re.MULTILINE)


def _parse_skill_metadata(text: str) -> dict[str, str]:
    """Extract name and version from SKILL.md YAML frontmatter."""
    match = _RE_FRONTMATTER.search(text)
    frontmatter = match.group(1) if match else text

    name_match = _RE_NAME.search(frontmatter)
    version_match = _RE_VERSION.search(frontmatter)

    return {
        "skill_name": name_match.group(1).strip() if name_match else "unknown",
        "version": version_match.group(1).strip() if version_match else "0.0.0",
    }


def _load_local_version(skill_dir: Path) -> dict[str, str]:
    """Read version metadata from the local SKILL.md frontmatter."""
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    return _parse_skill_metadata(text)


def _fetch_remote_metadata(skill_url: str) -> dict[str, str]:
    """Fetch and parse version metadata from the remote SKILL.md frontmatter."""
    with urlopen(skill_url, timeout=10) as response:
        text = response.read().decode("utf-8")
    return _parse_skill_metadata(text)


def _normalise_version(version: str) -> tuple[int, ...]:
    parts = []
    for part in version.strip().split("."):
        try:
            parts.append(int(part))
        except ValueError:
            break
    return tuple(parts)


def main() -> int:
    resource_dir = Path(__file__).resolve().parent
    skill_dir = resource_dir.parent  # skills/ai-qa/

    local_data = _load_local_version(skill_dir)
    local_version = local_data.get("version", "0.0.0")

    print(
        f"Checking {local_data.get('skill_name', 'skill')} version "
        f"{local_version} against {SKILL_URL}"
    )

    try:
        remote_data = _fetch_remote_metadata(SKILL_URL)
    except (OSError, URLError, ValueError) as exc:
        print(f"Could not fetch remote version metadata: {exc}")
        return 0

    remote_version = remote_data.get("version", local_version)
    if _normalise_version(remote_version) <= _normalise_version(local_version):
        print(f"Skill is up to date ({local_version}).")
        return 0

    print(f"Skill is outdated: local={local_version}, remote={remote_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
