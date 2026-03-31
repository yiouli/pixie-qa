"""``pixie init`` — scaffold the pixie_qa working directory.

Creates the standard directory layout for eval-driven development::

    pixie_qa/
        MEMORY.md
        datasets/
        tests/
        scripts/

The command is idempotent: existing files and directories are never
overwritten or deleted.  Running ``pixie init`` on an already-initialised
project is a safe no-op.
"""

from __future__ import annotations

from pathlib import Path

from pixie.config import get_config

#: Subdirectories to create under the pixie root.
_SUBDIRS = ("datasets", "tests", "scripts")

#: Default MEMORY.md content when creating a fresh file.
_MEMORY_TEMPLATE = """\
# Eval Notes

## How the application works

_Fill in after reading the source code._

## Evaluation plan

_Fill in after defining eval criteria._
"""


def init_pixie_dir(root: str | None = None) -> Path:
    """Create the pixie working directory and its standard layout.

    Args:
        root: Override for the pixie root directory.  When *None*,
              uses the value from :func:`pixie.config.get_config`
              (respects ``PIXIE_ROOT`` env var, defaults to ``pixie_qa``).

    Returns:
        The resolved :class:`~pathlib.Path` of the root directory.
    """
    if root is None:
        root = get_config().root

    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)

    for subdir in _SUBDIRS:
        (root_path / subdir).mkdir(parents=True, exist_ok=True)

    memory_path = root_path / "MEMORY.md"
    if not memory_path.exists():
        memory_path.write_text(_MEMORY_TEMPLATE)

    return root_path
