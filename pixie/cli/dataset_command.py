"""``pixie dataset`` CLI commands.

Provides two async operations for saving trace data from
:class:`~pixie.storage.store.ObservationStore` into a
:class:`~pixie.dataset.store.DatasetStore`:

- :func:`dataset_create` — create a new dataset from a trace's root span.
- :func:`dataset_append` — append a trace's root span to an existing dataset.
"""

from __future__ import annotations

from pixie.dataset.models import Dataset
from pixie.dataset.store import DatasetStore
from pixie.storage.evaluable import as_evaluable
from pixie.storage.store import ObservationStore


async def dataset_create(
    *,
    name: str,
    trace_id: str,
    observation_store: ObservationStore,
    dataset_store: DatasetStore,
) -> Dataset:
    """Create a new dataset containing the root span of a trace as an evaluable item.

    Args:
        name: Unique name for the new dataset.
        trace_id: Trace ID whose root span will be converted to an evaluable item.
        observation_store: Store to read spans from.
        dataset_store: Store to write the dataset to.

    Returns:
        The created ``Dataset``.

    Raises:
        ValueError: If no root observation exists for *trace_id*.
        FileExistsError: If a dataset with *name* already exists.
    """
    root = await observation_store.get_root(trace_id)
    evaluable = as_evaluable(root)
    return dataset_store.create(name, items=[evaluable])


async def dataset_append(
    *,
    name: str,
    trace_id: str,
    observation_store: ObservationStore,
    dataset_store: DatasetStore,
) -> Dataset:
    """Append the root span of a trace as an evaluable item to an existing dataset.

    Args:
        name: Name of the existing dataset.
        trace_id: Trace ID whose root span will be converted to an evaluable item.
        observation_store: Store to read spans from.
        dataset_store: Store to write the updated dataset to.

    Returns:
        The updated ``Dataset``.

    Raises:
        ValueError: If no root observation exists for *trace_id*.
        FileNotFoundError: If no dataset with *name* exists.
    """
    root = await observation_store.get_root(trace_id)
    evaluable = as_evaluable(root)
    return dataset_store.append(name, evaluable)
