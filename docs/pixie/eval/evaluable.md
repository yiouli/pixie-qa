Module pixie.eval.evaluable
===========================
Evaluable model — uniform data carrier for evaluators.

``TestCase`` defines the scenario (input, expectation, metadata) without
the actual output.  ``Evaluable`` extends it with actual output.
``NamedData`` provides a name+value pair for structured evaluation data.

The ``_Unset`` sentinel distinguishes *"expectation was never provided"*
from *"expectation is explicitly None"*.

Variables
---------

`UNSET`
:   Sentinel value: field was never set (as opposed to explicitly ``None``).

Classes
-------

`Evaluable(**data: Any)`
:   TestCase plus actual output — the full data carrier for evaluators.
    
    Inherits all ``TestCase`` fields and adds ``eval_output``.
    
    Attributes:
        eval_output: Named output data items from the observed operation
            (non-empty).
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pixie.eval.evaluable.TestCase
    * pydantic.main.BaseModel

    ### Class variables

    `eval_output: list[pixie.eval.evaluable.NamedData]`
    :

    `model_config`
    :

`NamedData(**data: Any)`
:   A named data value for evaluation input/output.
    
    Attributes:
        name: Identifier for this data item.
        value: The JSON-serializable value.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `name: str`
    :

    `value: JsonValue`
    :

`TestCase(**data: Any)`
:   Scenario definition without actual output.
    
    Defines the input, expectation, and metadata for a test case.
    Does not include the actual output — use ``Evaluable`` for that.
    
    Attributes:
        eval_input: Named input data items (non-empty).
        expectation: Expected/reference output for evaluation.
            Defaults to ``UNSET`` (not provided). May be explicitly
            set to ``None`` to indicate "no expectation".
        eval_metadata: Supplementary metadata (``None`` when absent).
        description: Human-readable description.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel

    ### Descendants

    * pixie.eval.evaluable.Evaluable

    ### Class variables

    `description: str | None`
    :

    `eval_input: list[pixie.eval.evaluable.NamedData]`
    :

    `eval_metadata: dict[str, JsonValue] | None`
    :

    `expectation: JsonValue | pixie.eval.evaluable._Unset`
    :

    `model_config`
    :