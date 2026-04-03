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
import json
from collections.abc import Callable
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


def resolve_evaluator_name(name: str) -> str:
    """Resolve short built-in name to fully qualified, or pass through FQN.

    Args:
        name: Either a bare class name (``"Factuality"``) for built-ins
            or a fully qualified name (``"myapp.evals.Custom"``).

    Returns:
        A fully qualified name suitable for :func:`_resolve_evaluator`.

    Raises:
        ValueError: If *name* has no dots and is not a known built-in.
    """
    name = name.strip()
    if "." in name:
        return name
    if name in BUILTIN_EVALUATOR_NAMES:
        return f"pixie.{name}"
    raise ValueError(
        f"Unknown evaluator {name!r}. "
        f"Use a fully qualified name for custom evaluators "
        f"(e.g. 'myapp.evals.{name}')."
    )


def _resolve_evaluator(name: str) -> Callable[..., Any]:
    """Import and instantiate an evaluator by name.

    Accepts both bare built-in names (``"Factuality"``) and fully
    qualified names (``"myapp.evals.Custom"``).

    Args:
        name: Evaluator name (bare or fully qualified).

    Returns:
        An instantiated evaluator object.
    """
    fqn = resolve_evaluator_name(name)
    module_path, _, class_name = fqn.rpartition(".")
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    instance: Callable[..., Any] = cls()
    return instance


async def _noop_runnable(eval_input: object) -> None:
    """No-op runnable for dataset items that already carry ``eval_output``."""


def _short_name(name: str) -> str:
    """Extract the class name from a possibly fully qualified name."""
    return name.rpartition(".")[2] or name


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


def load_dataset_entries(
    dataset_path: Path,
) -> tuple[str, list[tuple[Evaluable, list[str]]]]:
    """Load a dataset and return entries with their evaluator names.

    Items without an ``evaluators`` field are skipped.

    Args:
        dataset_path: Path to a dataset JSON file.

    Returns:
        A tuple of ``(dataset_name, entries)`` where each entry is
        ``(evaluable, evaluator_names)``.

    Raises:
        FileNotFoundError: If *dataset_path* does not exist.
    """
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    with open(dataset_path, encoding="utf-8") as f:
        data = json.load(f)

    dataset_name: str = data.get("name", dataset_path.stem)
    raw_items: list[dict[str, Any]] = data.get("items", [])

    entries: list[tuple[Evaluable, list[str]]] = []
    for item_data in raw_items:
        evaluator_list = item_data.get("evaluators")
        if not evaluator_list or not isinstance(evaluator_list, list):
            continue  # skip items without evaluators

        evaluator_names = [
            n.strip() for n in evaluator_list if isinstance(n, str) and n.strip()
        ]
        if not evaluator_names:
            continue

        evaluable = Evaluable.model_validate(item_data)
        entries.append((evaluable, evaluator_names))

    return dataset_name, entries
