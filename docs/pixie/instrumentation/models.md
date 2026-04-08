Module pixie.instrumentation.models
===================================
Pydantic models for trace log records.

Defines the structured log record types written by ``pixie trace``
and consumed by ``pixie format``:

- :class:`EntryInputLog` — the kwargs record (``type="kwargs"``).
- :class:`LLMSpanLog` — an LLM span record (``type="llm_span"``).

:class:`WrappedData` (from :mod:`pixie.instrumentation.wrap`) is the
model for wrap records (``type="wrap"``).

Classes
-------

`EntryInputLog(**data: Any)`
:   Kwargs record written at the start of a trace.
    
    Attributes:
        type: Always ``"kwargs"``.
        value: The runnable kwargs dictionary.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel

    ### Class variables

    `model_config`
    :

    `type: Literal['kwargs']`
    :

    `value: dict[str, JsonValue]`
    :

`LLMSpanLog(**data: Any)`
:   LLM span record capturing the semantically meaningful fields.
    
    Metadata-like fields (timing, IDs, token counts) are omitted because
    they are not useful for dataset construction via ``pixie format``.
    
    Attributes:
        type: Always ``"llm_span"``.
        operation: The LLM operation type (e.g. ``"chat"``).
        provider: LLM provider name (e.g. ``"openai"``).
        request_model: Model name from the request.
        response_model: Model name from the response.
        input_messages: Serialized input messages.
        output_messages: Serialized output messages.
        tool_definitions: Serialized tool definitions.
        finish_reasons: List of finish reasons.
        output_type: Output type string.
        error_type: Error type string.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel

    ### Class variables

    `error_type: str | None`
    :

    `finish_reasons: list[str]`
    :

    `input_messages: list[dict[str, typing.Any]]`
    :

    `model_config`
    :

    `operation: str | None`
    :

    `output_messages: list[dict[str, typing.Any]]`
    :

    `output_type: str | None`
    :

    `provider: str | None`
    :

    `request_model: str | None`
    :

    `response_model: str | None`
    :

    `tool_definitions: list[dict[str, typing.Any]]`
    :

    `type: Literal['llm_span']`
    :