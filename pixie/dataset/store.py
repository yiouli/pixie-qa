"""DatasetStore — JSON-file-backed CRUD for Dataset objects."""

from __future__ import annotations

import builtins
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pixie.config import get_config
from pixie.dataset.models import Dataset
from pixie.storage.evaluable import Evaluable


def _slugify(name: str) -> str:
    """Convert a dataset name to a filesystem-safe slug.

    Lowercase, replace non-alphanumeric runs with ``-``,
    strip leading/trailing ``-``.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise ValueError(f"Cannot slugify empty or non-alphanumeric name: {name!r}")
    return slug


class DatasetStore:
    """JSON-file-backed CRUD for ``Dataset`` objects.

    Each dataset is stored as ``<dataset_dir>/<slug>.json``.
    The directory is created on first write if it does not exist.

    Args:
        dataset_dir: Override directory. When ``None``, reads from
            ``PixieConfig.dataset_dir`` (env var ``PIXIE_DATASET_DIR``).
    """

    def __init__(self, dataset_dir: str | Path | None = None) -> None:
        if dataset_dir is not None:
            self._dir = Path(dataset_dir)
        else:
            self._dir = Path(get_config().dataset_dir)

    # -- helpers ----------------------------------------------------------

    def _path_for(self, name: str) -> Path:
        return self._dir / f"{_slugify(name)}.json"

    def _ensure_dir(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)

    # -- CRUD -------------------------------------------------------------

    def create(self, name: str, items: list[Evaluable] | None = None) -> Dataset:
        """Create a new dataset.

        Args:
            name: Unique dataset name.
            items: Initial evaluable items (default empty).

        Returns:
            The created ``Dataset``.

        Raises:
            FileExistsError: If a dataset with *name* already exists.
        """
        path = self._path_for(name)
        if path.exists():
            raise FileExistsError(f"Dataset already exists: {name!r}")
        dataset = Dataset(name=name, items=tuple(items) if items else ())
        self._write(path, dataset)
        return dataset

    def get(self, name: str) -> Dataset:
        """Load a dataset by name.

        Args:
            name: The dataset name.

        Returns:
            The loaded ``Dataset``.

        Raises:
            FileNotFoundError: If no dataset with *name* exists.
        """
        path = self._path_for(name)
        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {name!r}")
        return self._read(path)

    def list(self) -> list[str]:
        """Return the names of all stored datasets.

        Reads the ``name`` field from each JSON file in the dataset
        directory. Returns an empty list if the directory does not exist.
        """
        if not self._dir.exists():
            return []
        names: list[str] = []
        for p in sorted(self._dir.glob("*.json")):
            try:
                ds = self._read(p)
                names.append(ds.name)
            except Exception:
                continue  # skip malformed files
        return names

    def list_details(self) -> builtins.list[dict[str, Any]]:
        """Return metadata for every stored dataset.

        Each returned dict contains:

        - ``name``: dataset name
        - ``row_count``: number of evaluable items
        - ``created_at``: file creation timestamp (ISO 8601, UTC)
        - ``updated_at``: file last-modified timestamp (ISO 8601, UTC)

        Returns an empty list if the directory does not exist.
        """
        if not self._dir.exists():
            return []
        rows: list[dict[str, Any]] = []
        for p in sorted(self._dir.glob("*.json")):
            try:
                ds = self._read(p)
                stat = p.stat()
                rows.append(
                    {
                        "name": ds.name,
                        "row_count": len(ds.items),
                        "created_at": _timestamp_to_iso(stat.st_ctime),
                        "updated_at": _timestamp_to_iso(stat.st_mtime),
                    }
                )
            except Exception:
                continue  # skip malformed files
        return rows

    def delete(self, name: str) -> None:
        """Delete a dataset by name.

        Args:
            name: The dataset name.

        Raises:
            FileNotFoundError: If no dataset with *name* exists.
        """
        path = self._path_for(name)
        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {name!r}")
        path.unlink()

    def append(self, name: str, *items: Evaluable) -> Dataset:
        """Append items to an existing dataset.

        Args:
            name: The dataset name.
            *items: One or more ``Evaluable`` instances to add.

        Returns:
            The updated ``Dataset``.

        Raises:
            FileNotFoundError: If no dataset with *name* exists.
        """
        dataset = self.get(name)
        updated = Dataset(name=dataset.name, items=dataset.items + tuple(items))
        self._write(self._path_for(name), updated)
        return updated

    def remove(self, name: str, index: int) -> Dataset:
        """Remove an item by index from an existing dataset.

        Args:
            name: The dataset name.
            index: Zero-based index of the item to remove.

        Returns:
            The updated ``Dataset``.

        Raises:
            FileNotFoundError: If no dataset with *name* exists.
            IndexError: If *index* is out of range.
        """
        dataset = self.get(name)
        items = list(dataset.items)
        if index < 0 or index >= len(items):
            raise IndexError(
                f"Index {index} out of range for dataset {name!r} with {len(items)} items"
            )
        items.pop(index)
        updated = Dataset(name=dataset.name, items=tuple(items))
        self._write(self._path_for(name), updated)
        return updated

    # -- I/O helpers ------------------------------------------------------

    def _write(self, path: Path, dataset: Dataset) -> None:
        self._ensure_dir()
        data = dataset.model_dump(mode="json")
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def _read(self, path: Path) -> Dataset:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return Dataset.model_validate(raw)


def _timestamp_to_iso(ts: float) -> str:
    """Convert a POSIX timestamp to an ISO 8601 string (UTC)."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
