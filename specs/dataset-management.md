# Dataset Management — Implementation Spec

## Overview

Two related changes:

1. **Evaluable refactoring** — replace the `Protocol`-based `Evaluable` with a Pydantic `BaseModel`, embed `expected_output` directly into `Evaluable`, and remove the separate `expected_output` parameter from all evaluation function signatures.
2. **Dataset storage** — introduce `pixie.dataset`, a JSON-file-backed CRUD module for managing named collections of `Evaluable` items.

---

## 1. Evaluable Refactoring

### Current state

`Evaluable` is a `@runtime_checkable Protocol` in `pixie/storage/evaluable.py` with three read-only properties: `eval_input`, `eval_output`, `eval_metadata`. Expected output is passed as a separate `expected_output: Any` kwarg through `evaluate()`, `run_and_evaluate()`, `assert_pass()`, and into evaluator callables.

### New design

Replace the Protocol with a **Pydantic BaseModel**. Use Pydantic's `JsonValue` for JSON-compatible typing and a sentinel to distinguish "unset" from `None`.

#### File: `pixie/storage/evaluable.py`

```python
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic import JsonValue


class _Unset(Enum):
    """Sentinel to distinguish 'not provided' from ``None``."""
    UNSET = "UNSET"


UNSET = _Unset.UNSET
"""Sentinel value: field was never set (as opposed to explicitly ``None``)."""


class Evaluable(BaseModel):
    """Uniform data carrier for evaluators.

    All fields use Pydantic ``JsonValue`` to guarantee JSON
    round-trip fidelity.  ``expected_output`` uses a union with the
    ``_Unset`` sentinel so callers can distinguish *"expected output
    was not provided"* from *"expected output is explicitly None"*.

    Attributes:
        eval_input: The primary input to the observed operation.
        eval_output: The primary output of the observed operation.
        eval_metadata: Supplementary metadata (``None`` when absent).
        expected_output: The expected/reference output for evaluation.
            Defaults to ``UNSET`` (not provided). May be explicitly
            set to ``None`` to indicate "there is no expected output".
    """

    model_config = ConfigDict(frozen=True)

    eval_input: JsonValue = None
    eval_output: JsonValue = None
    eval_metadata: dict[str, JsonValue] | None = None
    expected_output: JsonValue | _Unset = Field(default=UNSET)
```

Key points:

- **Pydantic `BaseModel`** with `frozen=True` (immutable once created).
- **`JsonValue`** (from `pydantic`) for `eval_input`, `eval_output`, and `expected_output`. This ensures every value is JSON-serialisable.
- **`eval_metadata`** typed as `dict[str, JsonValue] | None` — `None` when absent, otherwise a string-keyed dict of JSON values.
- **`expected_output`** defaults to `UNSET` (the `_Unset` sentinel enum). This lets downstream code distinguish three states:
  - `UNSET` — no expected output was provided at all.
  - `None` — caller explicitly said "no expected output".
  - Any `JsonValue` — an actual reference value.
- Pydantic validators handle serialisation of the `_Unset` sentinel automatically via the enum's value (`"UNSET"`).

#### Remove `ObserveSpanEval`, `LLMSpanEval` classes

The adapter classes are replaced by the `as_evaluable()` factory which now returns an `Evaluable` model instance directly:

```python
from pixie.instrumentation.spans import (
    AssistantMessage,
    LLMSpan,
    ObserveSpan,
    TextContent,
)


def as_evaluable(span: ObserveSpan | LLMSpan) -> Evaluable:
    """Build an ``Evaluable`` from a span.

    ``expected_output`` is left as ``UNSET`` — span data never carries
    expected values.
    """
    if isinstance(span, LLMSpan):
        return _llm_span_to_evaluable(span)
    return _observe_span_to_evaluable(span)


def _observe_span_to_evaluable(span: ObserveSpan) -> Evaluable:
    return Evaluable(
        eval_input=span.input,
        eval_output=span.output,
        eval_metadata=span.metadata if span.metadata else None,
    )


def _llm_span_to_evaluable(span: LLMSpan) -> Evaluable:
    # Extract text from last output message
    output_text: str | None = None
    if span.output_messages:
        last: AssistantMessage = span.output_messages[-1]
        parts = [p.text for p in last.content if isinstance(p, TextContent)]
        output_text = "".join(parts) if parts else None

    metadata: dict[str, Any] = {
        "provider": span.provider,
        "request_model": span.request_model,
        "response_model": span.response_model,
        "operation": span.operation,
        "input_tokens": span.input_tokens,
        "output_tokens": span.output_tokens,
        "cache_read_tokens": span.cache_read_tokens,
        "cache_creation_tokens": span.cache_creation_tokens,
        "finish_reasons": span.finish_reasons,
        "error_type": span.error_type,
        "tool_definitions": span.tool_definitions,
    }

    return Evaluable(
        eval_input=span.input_messages,   # tuple[Message, ...]
        eval_output=output_text,
        eval_metadata=metadata,
    )
```

> **Note on `eval_input` for LLM spans:** `span.input_messages` is a tuple of frozen dataclasses. These are not natively JSON-serialisable. The implementation must convert them to JSON-compatible dicts (e.g. via `[msg.__dict__ for msg in span.input_messages]` or a custom serialiser) before constructing the `Evaluable`. The exact serialisation format should be determined during implementation, but the resulting value must be a valid `JsonValue`.

#### Update `pixie/storage/__init__.py`

Remove `ObserveSpanEval` and `LLMSpanEval` from exports. Keep `Evaluable`, `as_evaluable`, `UNSET`.

```python
from pixie.storage.evaluable import Evaluable, UNSET, as_evaluable
```

### Evaluation function signature changes

All `expected_output` / `expected_outputs` parameters are **removed** from evaluation functions. Evaluators read `evaluable.expected_output` directly.

#### `pixie/evals/evaluation.py`

**`Evaluator` protocol** — remove `expected_output` kwarg:

```python
class Evaluator(Protocol):
    async def __call__(
        self,
        evaluable: Evaluable,
        *,
        trace: list[ObservationNode] | None = None,
    ) -> Evaluation: ...
```

**`evaluate()`** — remove `expected_output` parameter:

```python
async def evaluate(
    evaluator: Callable[..., Any],
    evaluable: Evaluable,
    *,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
```

The function no longer forwards `expected_output` — evaluators access it from `evaluable.expected_output`.

#### `pixie/evals/eval_utils.py`

**`run_and_evaluate()`** — remove `expected_output`:

```python
async def run_and_evaluate(
    evaluator: Callable[..., Any],
    runnable: Callable[..., Any],
    input: Any,
    *,
    from_trace: Callable[[list[ObservationNode]], Evaluable] | None = None,
) -> Evaluation:
```

**`assert_pass()`** — remove `expected_outputs`:

```python
async def assert_pass(
    runnable: Callable[..., Any],
    inputs: list[Any],
    evaluators: list[Callable[..., Any]],
    *,
    passes: int = 1,
    pass_criteria: ... = None,
    from_trace: ... = None,
) -> None:
```

If the caller wants expected outputs, they construct `Evaluable` objects with `expected_output` set and use a dataset (see section 2) or a custom `from_trace` that injects the expected value.

The `assert_pass` signature changes to accept `Evaluable` items directly as an alternative to `(input, runnable)`:

```python
async def assert_pass(
    runnable: Callable[..., Any],
    inputs: list[Any],
    evaluators: list[Callable[..., Any]],
    *,
    evaluables: list[Evaluable] | None = None,
    passes: int = 1,
    pass_criteria: ... = None,
    from_trace: ... = None,
) -> None:
```

When `evaluables` is provided:

- The evaluables are used directly (each already carries its own `expected_output`).
- `inputs` list length must match `evaluables` list length.
- Each `evaluable` from the list is used as-is (or merged with trace-captured data if `from_trace` is also provided).

When `evaluables` is `None`:

- Current behaviour: run `runnable(input)`, build evaluable from trace.

#### `pixie/evals/scorers.py` — `AutoevalsAdapter`

Remove `expected_output` from `__call__` signature. Read expected from `evaluable.expected_output`:

```python
async def __call__(
    self,
    evaluable: Evaluable,
    *,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
```

Expected-value resolution priority (highest to lowest):

1. `evaluable.expected_output` (if not `UNSET`).
2. Constructor-provided `expected` (from factory function).
3. `evaluable.eval_metadata[expected_key]` (if metadata is not `None`).

### Files affected (Evaluable refactoring)

| File                                    | Change                                                                                                                                                           |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pixie/storage/evaluable.py`            | Replace Protocol with Pydantic BaseModel; add `expected_output` with `UNSET` sentinel; remove `ObserveSpanEval` / `LLMSpanEval` classes; update `as_evaluable()` |
| `pixie/storage/__init__.py`             | Update exports: remove `ObserveSpanEval`, `LLMSpanEval`; add `UNSET`                                                                                             |
| `pixie/evals/evaluation.py`             | Remove `expected_output` from `Evaluator` protocol and `evaluate()`                                                                                              |
| `pixie/evals/eval_utils.py`             | Remove `expected_output` / `expected_outputs` from `run_and_evaluate()` / `assert_pass()`; add optional `evaluables` param to `assert_pass()`                    |
| `pixie/evals/scorers.py`                | Remove `expected_output` from `AutoevalsAdapter.__call__`; read from `evaluable.expected_output`                                                                 |
| `pixie/evals/trace_helpers.py`          | Return `Evaluable` model instances (no adapter class changes needed since `as_evaluable` already returns `Evaluable`)                                            |
| `tests/pixie/storage/test_evaluable.py` | Rewrite for Pydantic model: construction, serialisation, `UNSET` vs `None`, `as_evaluable()`                                                                     |
| `tests/pixie/evals/test_evaluation.py`  | Update `evaluate()` calls — remove `expected_output` arg                                                                                                         |
| `tests/pixie/evals/test_eval_utils.py`  | Update `run_and_evaluate()` / `assert_pass()` calls                                                                                                              |
| `tests/pixie/evals/test_scorers.py`     | Update adapter tests — set `expected_output` on `Evaluable` instead of kwarg                                                                                     |
| `specs/evals-harness.md`                | Update signatures                                                                                                                                                |
| `specs/expected-output-in-evals.md`     | Replace or mark as superseded                                                                                                                                    |
| `specs/storage.md`                      | Update Evaluable section                                                                                                                                         |

### Backward compatibility

This is a **breaking change**. All existing evaluator callables that accept `expected_output` as a keyword argument must be updated to read `evaluable.expected_output` instead. The `AutoevalsAdapter` handles this internally. Custom user evaluators need migration.

---

## 2. Dataset Storage

### Package: `pixie/dataset/`

A dataset is a **named, ordered collection of `Evaluable` items** persisted as a JSON file. Management provides standard CRUD operations.

### Configuration

#### `pixie/config.py`

Add a `dataset_dir` field to `PixieConfig`:

```python
@dataclass(frozen=True)
class PixieConfig:
    db_path: str = "pixie_observations.db"
    db_engine: str = "sqlite"
    dataset_dir: str = "pixie_datasets"


def get_config() -> PixieConfig:
    return PixieConfig(
        db_path=os.environ.get("PIXIE_DB_PATH", PixieConfig.db_path),
        db_engine=os.environ.get("PIXIE_DB_ENGINE", PixieConfig.db_engine),
        dataset_dir=os.environ.get("PIXIE_DATASET_DIR", PixieConfig.dataset_dir),
    )
```

Environment variable: **`PIXIE_DATASET_DIR`** — absolute or relative path to the directory where dataset JSON files are stored. Defaults to `"pixie_datasets"` (relative to cwd).

### File layout

```
pixie/
  dataset/
    __init__.py        # public API re-exports
    models.py          # Dataset Pydantic model
    store.py           # DatasetStore (JSON file CRUD)
```

### Dataset model

#### File: `pixie/dataset/models.py`

```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pydantic import JsonValue

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
```

Key points:

- `name` is a non-empty string. It serves as the dataset's identity.
- `items` is an immutable tuple of `Evaluable` instances.
- The model is frozen — mutations go through the store API which returns new instances.

### Storage format

Each dataset is stored as a single JSON file:

- **Directory**: configured by `PIXIE_DATASET_DIR` (via `PixieConfig.dataset_dir`).
- **File name**: `<slugified-name>.json` where the slug is derived from `dataset.name` using a simple slugify (lowercase, replace non-alphanumeric runs with `-`, strip leading/trailing `-`).
- **File content**:

```json
{
  "name": "my-test-cases",
  "items": [
    {
      "eval_input": "What is 2+2?",
      "eval_output": null,
      "eval_metadata": null,
      "expected_output": "4"
    },
    {
      "eval_input": "Capital of France?",
      "eval_output": null,
      "eval_metadata": null,
      "expected_output": "Paris"
    }
  ]
}
```

Pydantic's `model_dump(mode="json")` / `model_validate` handles serialisation. The `_Unset` sentinel serialises as the string `"UNSET"` via the enum value; on deserialisation Pydantic reconstructs the `_Unset` enum member.

### DatasetStore

#### File: `pixie/dataset/store.py`

```python
from __future__ import annotations

import json
import re
from pathlib import Path

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
                f"Index {index} out of range for dataset {name!r} "
                f"with {len(items)} items"
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
```

### CRUD summary

| Operation  | Method                       | Behavior                                                    |
| ---------- | ---------------------------- | ----------------------------------------------------------- |
| **Create** | `store.create(name, items?)` | Create new dataset; raises `FileExistsError` if exists      |
| **Read**   | `store.get(name)`            | Load by name; raises `FileNotFoundError` if missing         |
| **List**   | `store.list()`               | Return all dataset names                                    |
| **Delete** | `store.delete(name)`         | Remove the JSON file; raises `FileNotFoundError` if missing |
| **Append** | `store.append(name, *items)` | Add items to end of existing dataset                        |
| **Remove** | `store.remove(name, index)`  | Remove item at index from existing dataset                  |

### Public API

#### File: `pixie/dataset/__init__.py`

```python
"""pixie.dataset — named collections of evaluable items.

Public API:
    - ``Dataset`` — Pydantic model: name + items
    - ``DatasetStore`` — JSON-file-backed CRUD
"""

from pixie.dataset.models import Dataset
from pixie.dataset.store import DatasetStore

__all__ = ["Dataset", "DatasetStore"]
```

---

## 3. Integration with Eval Harness

With `expected_output` embedded in `Evaluable`, and datasets providing lists of `Evaluable`, the eval harness can consume datasets directly:

```python
from pixie.dataset import DatasetStore
from pixie.evals import assert_pass

store = DatasetStore()
ds = store.get("qa-golden-set")

# Each item in ds.items is an Evaluable with expected_output already set
await assert_pass(
    runnable=my_qa_app,
    inputs=[item.eval_input for item in ds.items],
    evaluators=[FactualityEval()],
    evaluables=list(ds.items),
)
```

Or at the `evaluate()` level:

```python
from pixie.evals import evaluate

for item in ds.items:
    result = await evaluate(my_evaluator, item)
    # my_evaluator reads item.expected_output internally
```

---

## 4. Dependencies

- **New dependency**: `pydantic>=2.0` — for `Evaluable`, `Dataset` models and `JsonValue` type.
- **No other new external dependencies**.

Add to `pyproject.toml`:

```toml
dependencies = [
    ...,
    "pydantic>=2.0",
]
```

---

## 5. Tests

### `tests/pixie/storage/test_evaluable.py`

- `Evaluable` construction with all fields.
- `Evaluable` construction with defaults (`eval_input=None`, `expected_output=UNSET`).
- `expected_output` distinguishes `UNSET` vs `None` vs a value.
- `Evaluable` is frozen — assignment raises.
- `model_dump()` / `model_validate()` round-trip preserves all fields including `UNSET`.
- `as_evaluable()` from `ObserveSpan` produces correct `Evaluable`.
- `as_evaluable()` from `LLMSpan` produces correct `Evaluable` with text extraction.
- `as_evaluable()` always leaves `expected_output` as `UNSET`.
- `eval_metadata` accepts `None` or `dict[str, JsonValue]`.

### `tests/pixie/dataset/test_models.py`

- `Dataset` construction with name and items.
- `Dataset` rejects empty name.
- `Dataset` serialisation round-trip.
- `Dataset` is frozen.

### `tests/pixie/dataset/test_store.py`

- `_slugify` converts names correctly.
- `_slugify` raises on empty/non-alphanumeric input.
- `create` writes JSON file with correct content.
- `create` raises `FileExistsError` on duplicate.
- `get` loads dataset correctly.
- `get` raises `FileNotFoundError` for missing dataset.
- `list` returns all dataset names.
- `list` returns empty list when directory does not exist.
- `list` skips malformed JSON files.
- `delete` removes the file.
- `delete` raises `FileNotFoundError` for missing dataset.
- `append` adds items and persists.
- `remove` removes item by index and persists.
- `remove` raises `IndexError` for out-of-range index.
- `DatasetStore` respects `PIXIE_DATASET_DIR` env var.
- `DatasetStore` creates directory on first write.

### Updated eval tests

- All tests in `tests/pixie/evals/` must be updated to remove `expected_output` kwargs from `evaluate()`, `run_and_evaluate()`, `assert_pass()` calls and instead set `expected_output` on the `Evaluable` directly.

---

## 6. File Structure

```
pixie/
  config.py                       # add dataset_dir field
  storage/
    __init__.py                   # update exports
    evaluable.py                  # Pydantic BaseModel + UNSET sentinel
  dataset/
    __init__.py                   # public API
    models.py                     # Dataset model
    store.py                      # DatasetStore (JSON CRUD)
  evals/
    evaluation.py                 # remove expected_output from signatures
    eval_utils.py                 # remove expected_output(s) from signatures
    scorers.py                    # update AutoevalsAdapter
    trace_helpers.py              # (no changes needed)

tests/
  pixie/
    storage/
      test_evaluable.py           # rewrite for Pydantic model
    dataset/
      __init__.py
      test_models.py
      test_store.py
    evals/
      test_evaluation.py          # update
      test_eval_utils.py          # update
      test_scorers.py             # update
```

---

## 7. Non-Goals

- **Dataset versioning** — no version history or diffing. Overwriting is the update model.
- **Remote / cloud storage** — JSON files on local disk only for now.
- **Dataset import/export CLI** — no CLI commands in this iteration. Programmatic API only.
- **Schema migration** — the JSON format is defined by Pydantic model serialisation. If the model changes, old files may need manual migration.
- **Concurrent access safety** — no file locking. Single-writer assumption.
- **Large dataset optimisation** — entire dataset is loaded into memory. Suitable for evaluation-sized datasets (hundreds to low thousands of items), not for bulk data.
