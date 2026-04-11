"""Dataset-driven test runner for ``pixie test`` and ``pixie trace``.

Handles all non-CLI harness logic:

- Loading callables and runnables from ``filepath:name`` references
- Evaluator resolution (built-in and custom)
- Dataset parsing, validation, and loading
- Entry execution (runnable invocation + evaluation)
- Full dataset orchestration with concurrency

Usage::

    pixie test path/to/dataset.json       # single dataset
    pixie test path/to/dir/               # all datasets in dir tree
    pixie test                            # all datasets in pixie folder
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import inspect
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import (
    BaseModel,
    JsonValue,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

from pixie.eval.evaluable import (
    Evaluable,
    NamedData,
    TestCase,
    _Unset,
    collapse_named_data,
)
from pixie.eval.evaluation import evaluate
from pixie.harness.run_result import EntryResult, EvaluationResult, PendingEvaluation
from pixie.harness.runnable import get_runnable_args_type, is_runnable_class
from pixie.harness.trace_capture import current_entry_index, record_entry_kwargs
from pixie.instrumentation.wrap import (
    WrappedData,
    WrapRegistryMissError,
    WrapTypeMismatchError,
    clear_eval_input,
    clear_eval_output,
    get_eval_output,
    init_eval_output,
    set_eval_input,
)

_JSON_VALUE_ADAPTER: TypeAdapter[JsonValue] = TypeAdapter(JsonValue)

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

    The *base_dir* is added to :data:`sys.path` (if not already present)
    before loading the module so that the loaded code can use regular
    ``import`` statements to reference other project modules
    (e.g. ``from app import service``).

    Args:
        reference: Reference in ``filepath:callable_name`` format where
            *filepath* is relative to *base_dir*.
        base_dir: Directory to resolve relative file paths against.
            Also added to ``sys.path`` so the loaded module can import
            sibling packages.

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

    _ensure_on_sys_path(base_dir)

    spec = importlib.util.spec_from_file_location("_pixie_user_mod", file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec from {file_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return getattr(module, attr_name)


def _ensure_on_sys_path(directory: Path) -> None:
    """Add *directory* to :data:`sys.path` if not already present.

    Uses the resolved (absolute) directory string for comparison so that
    equivalent paths (``./src`` vs ``/abs/src``) are not duplicated.
    """
    dir_str = str(directory.resolve())
    if dir_str not in sys.path:
        sys.path.insert(0, dir_str)


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


def _clean_evaluator_list(raw: Any, *, allow_ellipsis: bool) -> list[str]:
    """Validate and normalize a list of evaluator name strings."""
    if not isinstance(raw, list):
        raise ValueError("'evaluators' must be a list of strings")
    result: list[str] = []
    for i, item in enumerate(raw, start=1):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"evaluator #{i} must be a non-empty string")
        name = item.strip()
        if name == "..." and not allow_ellipsis:
            raise ValueError("'...' is only allowed in row-level evaluators")
        result.append(name)
    return result


class DatasetEntry(TestCase):
    """A single entry (row) in a dataset.

    Each entry represents one test scenario.  Inherits all :class:`TestCase`
    fields (``eval_input``, ``expectation``, ``eval_metadata``,
    ``description``) and adds ``entry_kwargs`` and ``evaluators``.

    The evaluator list is resolved during :class:`Dataset` validation —
    if the entry omits ``evaluators``, it inherits the dataset-level
    defaults.  Use ``"..."`` in the entry's evaluators list to include
    the defaults **plus** additional evaluators.

    Example JSON::

        {
          "entry_kwargs": {"user_message": "What are your hours?"},
          "description": "Business hours question",
          "eval_input": [{"name": "profile", "value": {"tier": "gold"}}],
          "expectation": "Should mention Mon-Fri 9am-5pm",
          "evaluators": ["...", "ClosedQA"]
        }

    Attributes:
        entry_kwargs: Arguments fed to the runnable's ``run(args)`` method
            as a Pydantic model.  Keys must match the model's field names.
        evaluators: Evaluator names for this entry.  Omit to inherit
            dataset-level defaults.  Use ``"..."`` to include defaults
            plus additional evaluators.
    """

    entry_kwargs: dict[str, JsonValue]
    evaluators: list[str] = []

    @field_validator("evaluators", mode="before")
    @classmethod
    def _clean_evaluators(cls, v: Any) -> list[str]:
        if v is None:
            return []
        return _clean_evaluator_list(v, allow_ellipsis=True)

    @model_validator(mode="after")
    def _require_description(self) -> DatasetEntry:
        desc = self.description
        if not desc or not desc.strip():
            raise ValueError("description must be a non-empty string")
        return self


class Dataset(BaseModel):
    """Parsed dataset ready for evaluation.

    The JSON file is validated directly into this model via
    ``Dataset.model_validate(data)``.  All structural checks,
    evaluator resolution, and runnable importability are handled
    by field- and model-validators.

    Evaluator resolution order per entry:

    1. If the entry has its own ``evaluators`` list, use it
       (``"..."`` is expanded to the dataset-level defaults).
    2. If the entry omits ``evaluators``, the dataset-level
       ``evaluators`` are used as the default.
    3. If neither the entry nor the dataset defines evaluators,
       validation fails.

    Example JSON::

        {
          "name": "qa-golden-set",
          "runnable": "pixie_qa/scripts/run_app.py:AppRunnable",
          "evaluators": ["Factuality"],
          "entries": [
            {
              "entry_kwargs": {"user_message": "Hello"},
              "description": "Greeting",
              "eval_input": [{"name": "profile", "value": {}}],
              "expectation": "Friendly greeting"
            },
            {
              "entry_kwargs": {"user_message": "Help"},
              "description": "Help request",
              "eval_input": [{"name": "profile", "value": {}}],
              "expectation": "Offer assistance",
              "evaluators": ["...", "ClosedQA"]
            }
          ]
        }

    Attributes:
        name: Dataset display name.
        runnable: ``filepath:callable_name`` reference to the Runnable.
        evaluators: Dataset-level default evaluator names.  Applied to
            every entry that does not declare its own ``evaluators``.
        entries: List of dataset entries.
    """

    name: str = ""
    runnable: str
    evaluators: list[str] = []
    entries: list[DatasetEntry]

    @field_validator("runnable")
    @classmethod
    def _validate_runnable_format(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("'runnable' must be a non-empty string")
        return v

    @field_validator("evaluators", mode="before")
    @classmethod
    def _clean_default_evaluators(cls, v: Any) -> list[str]:
        if v is None:
            return []
        return _clean_evaluator_list(v, allow_ellipsis=False)

    @model_validator(mode="after")
    def _resolve_and_validate(self) -> Dataset:
        # Validate runnable is importable
        try:
            resolved = resolve_runnable_reference(self.runnable)
            if not callable(resolved):
                raise ValueError(
                    f"Runnable {self.runnable!r} does not resolve to a callable."
                )
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(
                f"Invalid runnable {self.runnable!r}: " f"{type(exc).__name__}: {exc}"
            ) from exc

        # Expand evaluators for each entry and collect all unique names
        all_names: set[str] = set(self.evaluators)
        for i, entry in enumerate(self.entries, start=1):
            expanded = _expand_evaluator_names(entry.evaluators, self.evaluators)
            expanded = [n.strip() for n in expanded if n.strip()]
            if not expanded:
                raise ValueError(
                    f"Entry #{i}: no evaluators resolved. "
                    "Set dataset-level 'evaluators' or row-level 'evaluators'."
                )
            all_names.update(expanded)
            entry.evaluators = expanded

        # Validate all unique evaluator names
        for name in sorted(all_names):
            try:
                resolve_evaluator_name(name)
                _resolve_evaluator(name)
            except Exception as exc:
                raise ValueError(
                    f"Invalid evaluator {name!r}: " f"{type(exc).__name__}: {exc}"
                ) from exc

        return self


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


def load_dataset(dataset_path: Path) -> Dataset:
    """Load a dataset and return a :class:`Dataset`.

    The dataset JSON is validated directly by :class:`Dataset`.

    Args:
        dataset_path: Path to a dataset JSON file.

    Returns:
        A :class:`Dataset` with resolved entries.

    Raises:
        FileNotFoundError: If *dataset_path* does not exist.
        ValueError: If dataset validation fails.
    """
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    with open(dataset_path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Top-level JSON value must be an object.")

    data.setdefault("name", dataset_path.stem)

    try:
        return Dataset.model_validate(data)
    except ValidationError as exc:
        parts: list[str] = []
        for err in exc.errors():
            loc = ".".join(str(part) for part in err["loc"]) if err["loc"] else ""
            msg = err["msg"]
            parts.append(f"{loc}: {msg}" if loc else msg)
        raise ValueError("Dataset validation failed:\n" + "\n".join(parts)) from exc


# ---------------------------------------------------------------------------
# Runnable resolution and execution
# ---------------------------------------------------------------------------


def resolve_runnable_reference(reference: str) -> Any:
    """Load a runnable from a ``filepath:callable_name`` reference.

    Args:
        reference: Reference in ``filepath:callable_name`` format.

    Returns:
        The resolved Python object (class or callable).

    Raises:
        ValueError: If *reference* is not in ``filepath:name`` format.
    """
    reference = reference.strip()
    if ":" not in reference:
        raise ValueError(
            f"Runnable must use filepath:name format "
            f"(e.g. 'pixie_qa/scripts/run_app.py:MyRunnable'), "
            f"got {reference!r}."
        )
    return _load_callable(reference, Path.cwd())


async def run_runnable(
    reference: str,
    kwargs: dict[str, Any],
) -> None:
    """Resolve, create, and run a Runnable with the given kwargs.

    Handles the full lifecycle: ``create()`` → ``setup()`` → ``run(args)``
    → ``teardown()``.

    For plain callables (non-Runnable), calls directly with kwargs dict.

    Args:
        reference: ``filepath:callable_name`` reference to the runnable.
        kwargs: Arguments to pass to the runnable.
    """
    resolved = resolve_runnable_reference(reference)

    if is_runnable_class(resolved):
        assert isinstance(resolved, type)
        args_type = get_runnable_args_type(resolved)
        instance = resolved.create()  # type: ignore[attr-defined]
        try:
            await instance.setup()
            args = args_type.model_validate(kwargs)
            await instance.run(args)
        finally:
            await instance.teardown()
    else:
        if inspect.iscoroutinefunction(resolved):
            await resolved(kwargs)
        else:
            resolved(kwargs)


def load_input_kwargs(input_path: str | Path) -> dict[str, Any]:
    """Load kwargs from a JSON file.

    Args:
        input_path: Path to a JSON file containing kwargs.

    Returns:
        The parsed kwargs dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the JSON is invalid or not a dict.
    """
    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(
            f"Input file must contain a JSON object, got {type(data).__name__}."
        )

    return data


# ---------------------------------------------------------------------------
# Entry execution and evaluation
# ---------------------------------------------------------------------------


async def evaluate_entry(
    evaluable: Evaluable,
    evaluator_names: list[str],
) -> EntryResult:
    """Run evaluators on a fully-populated evaluable and return an EntryResult.

    Evaluators that raise :class:`AgentEvaluationPending` are recorded as
    :class:`PendingEvaluation` entries instead of :class:`EvaluationResult`.

    Args:
        evaluable: The evaluation scenario with input, output, and metadata.
        evaluator_names: List of evaluator names to run.

    Returns:
        An EntryResult with evaluation scores and reasoning.
    """
    from pixie.eval.agent_evaluator import AgentEvaluationPending

    evaluators = [_resolve_evaluator(name) for name in evaluator_names]
    short_names = [_short_name(n) for n in evaluator_names]

    eval_results: list[EvaluationResult | PendingEvaluation] = []

    async def _run_one(
        ev: Callable[..., Any], name: str
    ) -> EvaluationResult | PendingEvaluation:
        try:
            result = await evaluate(ev, evaluable)
            return EvaluationResult(
                evaluator=name, score=result.score, reasoning=result.reasoning
            )
        except AgentEvaluationPending as pending:
            return PendingEvaluation(
                evaluator=pending.evaluator_name,
                criteria=pending.criteria,
            )

    results = await asyncio.gather(
        *(_run_one(ev, name) for ev, name in zip(evaluators, short_names, strict=True))
    )
    eval_results = list(results)

    exp_out = evaluable.expectation
    expectation = None if isinstance(exp_out, _Unset) or exp_out is None else exp_out

    return EntryResult(
        input=collapse_named_data(evaluable.eval_input),
        output=collapse_named_data(evaluable.eval_output),
        expected_output=expectation,
        description=evaluable.description,
        evaluations=eval_results,
    )


async def _run_entry(
    entry: DatasetEntry,
    runnable: Callable[..., Any],
    semaphore: asyncio.Semaphore,
    *,
    entry_index: int,
    args_type: type[BaseModel] | None = None,
) -> EntryResult:
    """Process a single dataset entry: call runnable, then evaluate.

    Sets up ``eval_input`` (for ``wrap(purpose="input")`` injection) and
    ``eval_output`` (populated by ``EvalCaptureLogProcessor``) before
    calling the runnable. After the call, captured bodies are validated
    into :class:`WrappedData` and converted to :class:`NamedData`.

    When *args_type* is provided (Runnable protocol), kwargs are validated
    into the Pydantic model before calling the runnable.

    Sets the ``current_entry_index`` context variable and records entry
    kwargs so that :class:`EntryTraceCollector` can build a full
    per-entry trace.

    Args:
        entry: The dataset entry to process.
        runnable: The runnable function or instance to execute.
        semaphore: Concurrency semaphore to limit parallel execution.
        args_type: Optional Pydantic model for runnable argument validation.
        entry_index: Entry index for trace capture association.

    Returns:
        An EntryResult with output and evaluation scores.
    """
    async with semaphore:
        current_entry_index.set(entry_index)
        record_entry_kwargs(entry_index, entry.entry_kwargs)
        init_eval_output()

        dependency_registry: dict[str, JsonValue] = {
            nd.name: nd.value for nd in entry.eval_input
        }
        set_eval_input(dependency_registry)

        runnable_result: Any = None
        try:
            if args_type is not None:
                args = args_type.model_validate(entry.entry_kwargs)
                runnable_result = await runnable(args)
            elif inspect.iscoroutinefunction(runnable):
                runnable_result = await runnable(entry.entry_kwargs)
            else:
                runnable_result = runnable(entry.entry_kwargs)
        except (WrapRegistryMissError, WrapTypeMismatchError) as exc:
            clear_eval_input()
            clear_eval_output()
            return EntryResult(
                input=collapse_named_data(entry.eval_input),
                output=None,
                expected_output=None,
                description=entry.description,
                evaluations=[
                    EvaluationResult(
                        evaluator="WrapError",
                        score=0.0,
                        reasoning=str(exc),
                    )
                ],
            )

        captured = get_eval_output() or []
        clear_eval_input()
        clear_eval_output()

    wrapped_output = [
        WrappedData.model_validate(wrapped_raw) for wrapped_raw in captured
    ]
    eval_output = [
        NamedData(name=wrapped.name, value=wrapped.data) for wrapped in wrapped_output
    ]
    if not eval_output:
        fallback_value: JsonValue
        try:
            fallback_value = _JSON_VALUE_ADAPTER.validate_python(runnable_result)
        except Exception:
            fallback_value = json.dumps(runnable_result, default=str)
        eval_output = [NamedData(name="output", value=fallback_value)]

    evaluable = Evaluable(
        eval_input=entry.eval_input,
        eval_output=eval_output,
        expectation=entry.expectation,
        eval_metadata=entry.eval_metadata,
        description=entry.description,
    )

    return await evaluate_entry(evaluable, entry.evaluators)


async def run_dataset(dataset_path: str) -> tuple[str, list[EntryResult]]:
    """Run evaluations for a single dataset and return the dataset name and results.

    **Concurrency model**: up to 4 entries run concurrently via
    ``asyncio.gather`` (gated by a semaphore).  Evaluators within
    each entry also run concurrently.  The ``Runnable.run()`` method
    **must be concurrency-safe** — see :class:`Runnable` for details.

    Rate limiting is enforced inside ``evaluate()`` when configured.

    When the dataset's runnable resolves to a :class:`Runnable` class,
    setup/teardown lifecycle hooks are called once around all entries,
    and each entry's kwargs are validated into the Runnable's args type.

    Args:
        dataset_path: Path to a dataset JSON file.

    Returns:
        A tuple of (dataset_name, list of EntryResult objects).

    Raises:
        FileNotFoundError: If the dataset file does not exist.
        ValueError: If the dataset fails validation.
    """
    dataset = load_dataset(Path(dataset_path))
    resolved = resolve_runnable_reference(dataset.runnable)
    semaphore = asyncio.Semaphore(4)

    if is_runnable_class(resolved):
        assert isinstance(resolved, type)  # narrow for type checker
        args_type = get_runnable_args_type(resolved)
        runnable_instance = resolved.create()  # type: ignore[attr-defined]
        try:
            await runnable_instance.setup()
            entry_tasks = [
                _run_entry(
                    entry,
                    runnable_instance.run,
                    semaphore,
                    args_type=args_type,
                    entry_index=i,
                )
                for i, entry in enumerate(dataset.entries)
            ]
            entry_results: list[EntryResult] = list(await asyncio.gather(*entry_tasks))
        finally:
            await runnable_instance.teardown()
    else:
        entry_tasks = [
            _run_entry(entry, resolved, semaphore, entry_index=i)
            for i, entry in enumerate(dataset.entries)
        ]
        entry_results = list(await asyncio.gather(*entry_tasks))

    return dataset.name, entry_results
