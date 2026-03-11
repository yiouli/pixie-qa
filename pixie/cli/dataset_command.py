"""``pixie dataset`` CLI commands.

Provides operations for managing datasets and saving trace spans as evaluable
items:

- :func:`dataset_create` — create a new empty dataset.
- :func:`dataset_list` — list datasets with basic information.
- :func:`dataset_save` — select a span from the latest trace and save it
  to a dataset.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import JsonValue

from pixie.dataset.models import Dataset
from pixie.dataset.store import DatasetStore
from pixie.storage.evaluable import UNSET, Evaluable, _Unset, as_evaluable
from pixie.storage.store import ObservationStore


def dataset_create(
    *,
    name: str,
    dataset_store: DatasetStore,
) -> Dataset:
    """Create a new empty dataset.

    Args:
        name: Unique name for the new dataset.
        dataset_store: Store to write the dataset to.

    Returns:
        The created ``Dataset``.

    Raises:
        FileExistsError: If a dataset with *name* already exists.
    """
    return dataset_store.create(name)


def dataset_list(
    *,
    dataset_store: DatasetStore,
) -> list[dict[str, Any]]:
    """Return metadata for every dataset.

    Each returned dict contains:
    - ``name``: dataset name
    - ``row_count``: number of evaluable items
    - ``created_at``: file creation timestamp (ISO 8601)
    - ``updated_at``: file last-modified timestamp (ISO 8601)
    """
    names = dataset_store.list()
    rows: list[dict[str, Any]] = []
    for name in names:
        ds = dataset_store.get(name)
        path = dataset_store._path_for(name)
        stat = path.stat()
        rows.append(
            {
                "name": ds.name,
                "row_count": len(ds.items),
                "created_at": _timestamp_to_iso(stat.st_ctime),
                "updated_at": _timestamp_to_iso(stat.st_mtime),
            }
        )
    return rows


def format_dataset_table(rows: list[dict[str, Any]]) -> str:
    """Format dataset metadata rows as an aligned CLI table.

    Args:
        rows: List of dicts from :func:`dataset_list`.

    Returns:
        A multi-line string suitable for printing.
    """
    if not rows:
        return "No datasets found."

    headers = ["Name", "Rows", "Created", "Updated"]
    data = [
        [r["name"], str(r["row_count"]), r["created_at"], r["updated_at"]]
        for r in rows
    ]

    col_widths = [len(h) for h in headers]
    for row in data:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    def _fmt_row(cells: list[str]) -> str:
        return "  ".join(c.ljust(col_widths[i]) for i, c in enumerate(cells))

    lines = [_fmt_row(headers), _fmt_row(["-" * w for w in col_widths])]
    for row in data:
        lines.append(_fmt_row(row))
    return "\n".join(lines)


async def dataset_save(
    *,
    name: str,
    observation_store: ObservationStore,
    dataset_store: DatasetStore,
    select: str = "root",
    span_name: str | None = None,
    expected_output: JsonValue | _Unset = UNSET,
    notes: str | None = None,
) -> Dataset:
    """Select a span from the latest trace and save it to a dataset.

    Fetches the most recent trace from the observation store, selects
    a span according to *select*, converts it to an ``Evaluable``, then
    appends it to the named dataset.

    Args:
        name: Name of the dataset to save to (must exist).
        observation_store: Store to read spans from.
        dataset_store: Store to write the updated dataset to.
        select: Selection mode — ``"root"``, ``"last_llm_call"``, or
            ``"by_name"``. Defaults to ``"root"``.
        span_name: Span name to match when *select* is ``"by_name"``.
            Required when *select* is ``"by_name"``.
        expected_output: If provided, set on the evaluable. When
            ``UNSET`` (default), the evaluable's ``expected_output``
            is left as ``UNSET``.
        notes: Optional notes string to attach to the evaluable's
            ``eval_metadata`` under the ``"notes"`` key.

    Returns:
        The updated ``Dataset``.

    Raises:
        ValueError: If no traces exist, or no matching span found.
        FileNotFoundError: If no dataset with *name* exists.
    """
    traces = await observation_store.list_traces(limit=1)
    if not traces:
        raise ValueError("No traces found in the observation store.")
    trace_id: str = traces[0]["trace_id"]

    span = await _select_span(
        observation_store=observation_store,
        trace_id=trace_id,
        select=select,
        span_name=span_name,
    )

    evaluable = as_evaluable(span)

    # Apply expected_output if provided
    if not isinstance(expected_output, _Unset):
        evaluable = Evaluable(
            eval_input=evaluable.eval_input,
            eval_output=evaluable.eval_output,
            eval_metadata=evaluable.eval_metadata,
            expected_output=expected_output,
        )

    # Apply notes if provided
    if notes is not None:
        existing_meta = dict(evaluable.eval_metadata) if evaluable.eval_metadata else {}
        existing_meta["notes"] = notes
        evaluable = Evaluable(
            eval_input=evaluable.eval_input,
            eval_output=evaluable.eval_output,
            eval_metadata=existing_meta,
            expected_output=evaluable.expected_output,
        )

    return dataset_store.append(name, evaluable)


async def _select_span(
    *,
    observation_store: ObservationStore,
    trace_id: str,
    select: str,
    span_name: str | None,
) -> Any:
    """Select a span from a trace according to the selection mode."""
    if select == "root":
        return await observation_store.get_root(trace_id)

    if select == "last_llm_call":
        span = await observation_store.get_last_llm(trace_id)
        if span is None:
            raise ValueError(f"No LLM span found in trace {trace_id}.")
        return span

    if select == "by_name":
        if not span_name:
            raise ValueError("--span-name is required when selection mode is 'by_name'.")
        matches = await observation_store.get_by_name(span_name, trace_id=trace_id)
        if not matches:
            raise ValueError(
                f"No span named {span_name!r} found in trace {trace_id}."
            )
        # Select the latest (last by started_at — get_by_name returns ASC order)
        return matches[-1]

    raise ValueError(f"Unknown selection mode: {select!r}")


def _timestamp_to_iso(ts: float) -> str:
    """Convert a POSIX timestamp to an ISO 8601 string (UTC)."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
