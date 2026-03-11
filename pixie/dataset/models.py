"""Dataset model — a named collection of evaluable items."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from pixie.storage.evaluable import Evaluable


class Dataset(BaseModel):
    """A named collection of evaluable items.

    Attributes:
        name: Unique human-readable name for the dataset.
        items: Ordered list of evaluable entries.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., min_length=1)
    items: tuple[Evaluable, ...] = ()
