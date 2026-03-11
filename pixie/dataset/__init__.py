"""pixie.dataset — named collections of evaluable items.

Public API:
    - ``Dataset`` — Pydantic model: name + items
    - ``DatasetStore`` — JSON-file-backed CRUD
"""

from pixie.dataset.models import Dataset
from pixie.dataset.store import DatasetStore

__all__ = ["Dataset", "DatasetStore"]
