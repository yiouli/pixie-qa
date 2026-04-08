Module pixie.harness.runner
===========================
Dataset-driven test runner for ``pixie test`` and ``pixie trace``.

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

Variables
---------

`BUILTIN_EVALUATOR_NAMES: frozenset[str]`
:   Names of all built-in evaluators exported from ``pixie``.
    When a dataset uses a bare name (no dots), it is looked up here.

Functions
---------

`def discover_dataset_files(path: str) ‑> list[pathlib.Path]`
:   Find all dataset JSON files under *path*.
    
    Args:
        path: A ``.json`` file, a directory, or ``"."`` for current dir.
    
    Returns:
        Sorted list of dataset file paths.

`async def evaluate_entry(evaluable: Evaluable, evaluator_names: list[str]) ‑> pixie.harness.run_result.EntryResult`
:   Run evaluators on a fully-populated evaluable and return an EntryResult.
    
    Args:
        evaluable: The evaluation scenario with input, output, and metadata.
        evaluator_names: List of evaluator names to run.
    
    Returns:
        An EntryResult with evaluation scores and reasoning.

`def load_dataset(dataset_path: Path) ‑> pixie.harness.runner.Dataset`
:   Load a dataset and return a :class:`Dataset`.
    
    The dataset JSON is validated directly by :class:`Dataset`.
    
    Args:
        dataset_path: Path to a dataset JSON file.
    
    Returns:
        A :class:`Dataset` with resolved entries.
    
    Raises:
        FileNotFoundError: If *dataset_path* does not exist.
        ValueError: If dataset validation fails.

`def load_input_kwargs(input_path: str | Path) ‑> dict[str, typing.Any]`
:   Load kwargs from a JSON file.
    
    Args:
        input_path: Path to a JSON file containing kwargs.
    
    Returns:
        The parsed kwargs dictionary.
    
    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the JSON is invalid or not a dict.

`def resolve_evaluator_name(name: str) ‑> str`
:   Resolve short built-in name or validate a custom evaluator reference.
    
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

`def resolve_runnable_reference(reference: str) ‑> Any`
:   Load a runnable from a ``filepath:callable_name`` reference.
    
    Args:
        reference: Reference in ``filepath:callable_name`` format.
    
    Returns:
        The resolved Python object (class or callable).
    
    Raises:
        ValueError: If *reference* is not in ``filepath:name`` format.

`async def run_dataset(dataset_path: str) ‑> tuple[str, list[pixie.harness.run_result.EntryResult]]`
:   Run evaluations for a single dataset and return the dataset name and results.
    
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

`async def run_entry(entry: DatasetEntry, runnable: Callable[..., Any], semaphore: asyncio.Semaphore, *, args_type: type[BaseModel] | None = None) ‑> pixie.harness.run_result.EntryResult`
:   Process a single dataset entry: call runnable, then evaluate.
    
    Sets up ``eval_input`` (for ``wrap(purpose="input")`` injection) and
    ``eval_output`` (populated by ``EvalCaptureLogProcessor``) before
    calling the runnable. After the call, captured bodies are validated
    into :class:`WrappedData` and converted to :class:`NamedData`.
    
    When *args_type* is provided (Runnable protocol), kwargs are validated
    into the Pydantic model before calling the runnable.
    
    Args:
        entry: The dataset entry to process.
        runnable: The runnable function or instance to execute.
        semaphore: Concurrency semaphore to limit parallel execution.
        args_type: Optional Pydantic model for runnable argument validation.
    
    Returns:
        An EntryResult with output and evaluation scores.

`async def run_runnable(reference: str, kwargs: dict[str, Any]) ‑> None`
:   Resolve, create, and run a Runnable with the given kwargs.
    
    Handles the full lifecycle: ``create()`` → ``setup()`` → ``run(args)``
    → ``teardown()``.
    
    For plain callables (non-Runnable), calls directly with kwargs dict.
    
    Args:
        reference: ``filepath:callable_name`` reference to the runnable.
        kwargs: Arguments to pass to the runnable.

Classes
-------

`Dataset(**data: Any)`
:   Parsed dataset ready for evaluation.
    
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
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel

    ### Class variables

    `entries: list[pixie.harness.runner.DatasetEntry]`
    :

    `evaluators: list[str]`
    :

    `model_config`
    :

    `name: str`
    :

    `runnable: str`
    :

`DatasetEntry(**data: Any)`
:   A single entry (row) in a dataset.
    
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
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pixie.eval.evaluable.TestCase
    * pydantic.main.BaseModel

    ### Class variables

    `entry_kwargs: dict[str, JsonValue]`
    :

    `evaluators: list[str]`
    :

    `model_config`
    :