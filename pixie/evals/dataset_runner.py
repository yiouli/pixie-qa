"""Dataset-driven test runner for ``pixie test``.

Processes dataset JSON files where each row specifies its own evaluators.
Built-in evaluator names (no dots) are auto-resolved to ``pixie.{Name}``.
Custom evaluators use fully qualified names.

Usage::

    pixie test path/to/dataset.json       # single dataset
    pixie test path/to/dir/               # all datasets in dir tree
    pixie test                            # all datasets in pixie folder
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from pixie.storage.evaluable import Evaluable

#: Names of all built-in evaluators exported from ``pixie``.
#: When a dataset uses a bare name (no dots), it is looked up here.
BUILTIN_EVALUATOR_NAMES: frozenset[str] = frozenset(
    {
        "LevenshteinMatch",
        "ExactMatch",
        "NumericDiff",
        "JSONDiff",
        "ValidJSON",
        "ListContains",
        "EmbeddingSimilarity",
        "Factuality",
        "ClosedQA",
        "Battle",
        "Humor",
        "Security",
        "Sql",
        "Summary",
        "Translation",
        "Possible",
        "Moderation",
        "ContextRelevancy",
        "Faithfulness",
        "AnswerRelevancy",
        "AnswerCorrectness",
    }
)


def _load_callable(reference: str, base_dir: Path) -> Any:
    """Load a Python object from a ``filepath:name`` reference.

    Uses :func:`importlib.util.spec_from_file_location` to load the
    ``.py`` file directly from disk without any module/package resolution.

    Args:
        reference: Reference in ``filepath:callable_name`` format where
            *filepath* is relative to *base_dir*.
        base_dir: Directory to resolve relative file paths against.

    Returns:
        The resolved Python object (function, class, or instance).

    Raises:
        ValueError: If *reference* does not contain ``:``.
        FileNotFoundError: If the resolved file does not exist.
        ImportError: If the module cannot be loaded from the file.
        AttributeError: If the named attribute does not exist.
    """
    if ":" not in reference:
        raise ValueError(f"Reference must use filepath:name format, got {reference!r}.")
    file_part, attr_name = reference.rsplit(":", 1)
    file_path = (base_dir / file_part).resolve()

    if not file_path.is_file():
        raise FileNotFoundError(f"Module file not found: {file_path}")

    spec = importlib.util.spec_from_file_location("_pixie_user_mod", file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec from {file_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return getattr(module, attr_name)


def resolve_evaluator_name(name: str) -> str:
    """Resolve short built-in name or validate a custom evaluator reference.

    Args:
        name: Either a bare class name (``"Factuality"``) for built-ins
            or a ``filepath:callable_name`` reference for custom evaluators
            (e.g. ``"pixie_qa/evaluators.py:ConciseVoiceStyle"``).

    Returns:
        A resolved evaluator name: ``"pixie.{Name}"`` for built-ins,
        or the original ``filepath:name`` reference for custom evaluators.

    Raises:
        ValueError: If *name* is not a known built-in and does not use
            the ``filepath:name`` format.
    """
    name = name.strip()
    if ":" in name:
        return name
    if name in BUILTIN_EVALUATOR_NAMES:
        return f"pixie.{name}"
    raise ValueError(
        f"Unknown evaluator {name!r}. "
        f"Built-in evaluators use bare names (e.g. 'Factuality'). "
        f"Custom evaluators use filepath:name format "
        f"(e.g. 'pixie_qa/evaluators.py:{name}')."
    )


def _resolve_evaluator(name: str) -> Callable[..., Any]:
    """Import and return an evaluator by name.

    Accepts bare built-in names (``"Factuality"``) and
    ``filepath:callable_name`` references for custom evaluators
    (e.g. ``"pixie_qa/evaluators.py:ConciseVoiceStyle"``).

    The resolved attribute can be:

    - A **class** — instantiated via ``cls()``.
    - A **zero-arg factory function** (e.g. built-in ``ExactMatch``) —
      called to produce the evaluator instance.
    - A **function with required parameters** (evaluator function) —
      returned as-is.
    - A **pre-instantiated callable** (e.g. the return value of
      ``create_llm_evaluator()``) — returned as-is.

    Args:
        name: Evaluator name — bare built-in name or ``filepath:name``.

    Returns:
        A callable evaluator (class instance, function, or closure).

    Raises:
        TypeError: If the resolved attribute is not callable.
    """
    fqn = resolve_evaluator_name(name)

    if ":" in fqn:
        attr = _load_callable(fqn, Path.cwd())
    else:
        module_path, _, attr_name = fqn.rpartition(".")
        module = importlib.import_module(module_path)
        attr = getattr(module, attr_name)

    # Classes are instantiated (e.g. class-based evaluators).
    if isinstance(attr, type):
        instance: Callable[..., Any] = attr()
        return instance

    # Functions: distinguish zero-arg factories (like built-in ExactMatch)
    # from evaluator functions that take evaluable as the first parameter.
    if inspect.isfunction(attr):
        sig = inspect.signature(attr)
        required = [
            p
            for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty
            and p.kind
            not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        ]
        if not required:
            # Zero-arg factory → call to produce evaluator instance.
            factory_result: Callable[..., Any] = attr()
            return factory_result
        # Has required params → evaluator function itself.
        func_eval: Callable[..., Any] = attr
        return func_eval

    # Callable instances (e.g. create_llm_evaluator result): use as-is.
    if callable(attr):
        callable_eval: Callable[..., Any] = attr
        return callable_eval

    raise TypeError(
        f"Evaluator {name!r} resolved to {type(attr).__name__}, "
        f"which is not callable."
    )


def _resolve_runnable(reference: str) -> Callable[..., Any]:
    """Load a runnable function from a ``filepath:callable_name`` reference.

    Args:
        reference: Reference in ``filepath:callable_name`` format
            (e.g. ``"pixie_qa/scripts/run_app.py:run_app"``).
            The file path is relative to the current working directory.

    Returns:
        The resolved callable.

    Raises:
        ValueError: If *reference* does not use ``filepath:name`` format.
    """
    reference = reference.strip()
    if ":" not in reference:
        raise ValueError(
            f"Runnable must use filepath:name format "
            f"(e.g. 'pixie_qa/scripts/run_app.py:run_app'), "
            f"got {reference!r}."
        )
    func: Callable[..., Any] = _load_callable(reference, Path.cwd())
    return func


async def _noop_runnable(eval_input: object) -> None:
    """No-op runnable for dataset items that already carry ``eval_output``."""


def _short_name(name: str) -> str:
    """Extract the short callable name from a reference.

    Handles both ``filepath:callable_name`` and ``module.ClassName`` formats.
    """
    if ":" in name:
        return name.rsplit(":", 1)[1]
    return name.rpartition(".")[2] or name


def _expand_evaluator_names(
    row_evaluators: list[str] | None,
    default_evaluators: list[str],
) -> list[str]:
    """Resolve row-level evaluator names against defaults.

    Rules:
    - If *row_evaluators* is ``None`` or empty, use *default_evaluators*.
    - ``"..."`` in the row list is replaced with all *default_evaluators*.
    - Otherwise the row list is used as-is.

    Args:
        row_evaluators: Evaluator names declared on the dataset item.
        default_evaluators: Dataset-level default evaluator names.

    Returns:
        The resolved evaluator name list.
    """
    if not row_evaluators:
        return list(default_evaluators)

    result: list[str] = []
    for name in row_evaluators:
        if name.strip() == "...":
            result.extend(default_evaluators)
        else:
            result.append(name)
    return result


@dataclass(frozen=True)
class LoadedDataset:
    """Parsed dataset ready for evaluation.

    Attributes:
        name: Dataset display name.
        runnable: ``filepath:callable_name`` reference for the runnable.
        entries: List of ``(evaluable, evaluator_names)`` pairs.
    """

    name: str
    runnable: str
    entries: list[tuple[Evaluable, list[str]]] = field(default_factory=list)


def discover_dataset_files(path: str) -> list[Path]:
    """Find all dataset JSON files under *path*.

    Args:
        path: A ``.json`` file, a directory, or ``"."`` for current dir.

    Returns:
        Sorted list of dataset file paths.
    """
    target = Path(path)
    if target.is_file() and target.suffix == ".json":
        return [target]
    if target.is_dir():
        return sorted(target.rglob("*.json"))
    return []


def _parse_evaluator_list(
    raw: Any,
    *,
    allow_ellipsis: bool,
    location: str,
    errors: list[str],
) -> list[str]:
    """Parse evaluator list while collecting validation errors."""
    if not isinstance(raw, list):
        errors.append(f"{location}: 'evaluators' must be a list of strings.")
        return []

    names: list[str] = []
    for i, value in enumerate(raw, start=1):
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{location}: evaluator #{i} must be a non-empty string.")
            continue

        name = value.strip()
        if name == "..." and not allow_ellipsis:
            errors.append(f"{location}: '...' is only allowed in row-level evaluators.")
            continue
        names.append(name)

    return names


def _validate_evaluator_names(
    names: list[str],
    *,
    location: str,
    errors: list[str],
) -> None:
    """Validate evaluator names by checking resolution and importability."""
    for name in names:
        try:
            resolve_evaluator_name(name)
            _resolve_evaluator(name)
        except Exception as exc:  # pragma: no cover - exact type varies by import path
            errors.append(
                f"{location}: invalid evaluator {name!r} ({type(exc).__name__}: {exc})."
            )


def validate_dataset_file(dataset_path: Path) -> list[str]:
    """Validate a dataset file and return a list of human-readable errors."""
    if not dataset_path.exists():
        return [f"{dataset_path}: dataset not found."]

    try:
        with open(dataset_path, encoding="utf-8") as f:
            data = json.load(f)
    except JSONDecodeError as exc:
        return [f"{dataset_path}: invalid JSON ({exc.msg} at line {exc.lineno})."]

    errors: list[str] = []
    if not isinstance(data, dict):
        return [f"{dataset_path}: top-level JSON value must be an object."]

    runnable_raw = data.get("runnable")
    if not isinstance(runnable_raw, str) or not runnable_raw.strip():
        errors.append(
            f"{dataset_path}: missing required top-level 'runnable' (non-empty string)."
        )
    else:
        runnable = runnable_raw.strip()
        try:
            resolved = _resolve_runnable(runnable)
            if not callable(resolved):
                errors.append(
                    f"{dataset_path}: runnable {runnable!r} does not resolve to a callable."
                )
        except Exception as exc:  # pragma: no cover - exact type varies by import path
            errors.append(
                f"{dataset_path}: invalid runnable {runnable!r} ({type(exc).__name__}: {exc})."
            )

    default_evaluators_raw = data.get("evaluators", [])
    default_evaluators = _parse_evaluator_list(
        default_evaluators_raw,
        allow_ellipsis=False,
        location=f"{dataset_path} (dataset defaults)",
        errors=errors,
    )
    _validate_evaluator_names(
        default_evaluators,
        location=f"{dataset_path} (dataset defaults)",
        errors=errors,
    )

    items_raw = data.get("items", [])
    if not isinstance(items_raw, list):
        errors.append(f"{dataset_path}: 'items' must be a list.")
        return errors

    for idx, row in enumerate(items_raw, start=1):
        row_location = f"{dataset_path} item #{idx}"
        if not isinstance(row, dict):
            errors.append(f"{row_location}: item must be an object.")
            continue

        description = row.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append(
                f"{row_location}: missing required 'description' (non-empty string)."
            )

        row_evaluators: list[str] | None = None
        if "evaluators" in row:
            row_evaluators = _parse_evaluator_list(
                row.get("evaluators"),
                allow_ellipsis=True,
                location=row_location,
                errors=errors,
            )

        resolved_evaluators = _expand_evaluator_names(
            row_evaluators, default_evaluators
        )
        resolved_evaluators = [
            name.strip() for name in resolved_evaluators if name.strip()
        ]
        if not resolved_evaluators:
            errors.append(
                f"{row_location}: no evaluators resolved. "
                "Set dataset-level 'evaluators' or row-level 'evaluators'."
            )
            continue

        # Validate concrete resolved names only ("..." is expanded away above).
        _validate_evaluator_names(
            [name for name in resolved_evaluators if name != "..."],
            location=row_location,
            errors=errors,
        )

    return errors


def _is_new_format_item(item_data: dict[str, Any]) -> bool:
    """Return True if the item uses the new entry_input/dependency_input format."""
    return "entry_input" in item_data or "dependency_input" in item_data


def _build_evaluable_new_format(item_data: dict[str, Any]) -> Evaluable:
    """Build an :class:`Evaluable` from a new-format dataset item.

    New format items have ``entry_input`` and optional ``dependency_input``.
    ``dependency_input`` values are jsonpickle-serialized strings keyed by
    wrap name.
    """
    entry_input: Any = item_data.get("entry_input")
    dependency_input_raw = item_data.get("dependency_input") or {}
    dependency_input: dict[str, str] = {}
    for k, v in dependency_input_raw.items():
        if not isinstance(v, str):
            raise ValueError(
                f"dependency_input[{k!r}] must be a jsonpickle-serialized string, "
                f"got {type(v).__name__}. Encode the value with jsonpickle.encode() "
                f"before storing it in the dataset."
            )
        dependency_input[k] = v
    # Build metadata that includes dependency_input for evaluator context.
    meta: dict[str, Any] = {}
    if dependency_input:
        meta["dependency_input"] = dependency_input

    evaluable_data = {
        k: v
        for k, v in item_data.items()
        if k not in ("entry_input", "dependency_input", "eval_input", "eval_metadata")
    }
    evaluable_data["eval_input"] = entry_input
    evaluable_data["eval_metadata"] = meta or None
    return Evaluable.model_validate(evaluable_data)


def load_dataset_entries(
    dataset_path: Path,
) -> LoadedDataset:
    """Load a dataset and return a :class:`LoadedDataset`.

        The dataset JSON requires:

        - top-level ``runnable`` (str) — ``filepath:callable_name`` reference
            to a function that produces ``eval_output`` from ``eval_input``.
        - top-level ``items`` (list[dict]) — dataset entries.
        - per-item ``description`` (str).
        - at least one evaluator per item, via row-level ``evaluators`` or
            dataset-level default ``evaluators``.

        Each item may use either:

        - **New format**: ``entry_input`` (dict) + optional ``dependency_input``
          (dict[str, str] of jsonpickle-serialized values).  The runnable is
          called with ``entry_input`` only; dependency data is injected via
          ``wrap()``.
        - **Legacy format**: ``eval_input`` is passed directly to the runnable,
          and the runnable's return value becomes ``eval_output``.

    Args:
        dataset_path: Path to a dataset JSON file.

    Returns:
        A :class:`LoadedDataset` with resolved entries.

    Raises:
        FileNotFoundError: If *dataset_path* does not exist.
        ValueError: If dataset validation fails.
    """
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    errors = validate_dataset_file(dataset_path)
    if errors:
        message = "Dataset validation failed:\n" + "\n".join(errors)
        raise ValueError(message)

    with open(dataset_path, encoding="utf-8") as f:
        data = json.load(f)

    dataset_name: str = data.get("name", dataset_path.stem)
    runnable = str(data["runnable"]).strip()
    default_evaluators_raw: list[str] = data.get("evaluators", [])
    default_evaluators = [
        n.strip() for n in default_evaluators_raw if isinstance(n, str) and n.strip()
    ]
    raw_items: list[dict[str, Any]] = data.get("items", [])

    entries: list[tuple[Evaluable, list[str]]] = []
    for item_data in raw_items:
        row_evaluators_raw = item_data.get("evaluators")
        if isinstance(row_evaluators_raw, list):
            row_evaluators = [n for n in row_evaluators_raw if isinstance(n, str)]
        else:
            row_evaluators = None

        evaluator_names = _expand_evaluator_names(row_evaluators, default_evaluators)
        evaluator_names = [n.strip() for n in evaluator_names if n.strip()]

        if _is_new_format_item(item_data):
            evaluable = _build_evaluable_new_format(item_data)
        else:
            evaluable = Evaluable.model_validate(item_data)

        entries.append((evaluable, evaluator_names))

    return LoadedDataset(
        name=dataset_name,
        runnable=runnable,
        entries=entries,
    )
