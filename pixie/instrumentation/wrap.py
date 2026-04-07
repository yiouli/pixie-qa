"""``pixie.wrap`` — data-oriented observation API.

``wrap()`` observes a data value or callable at a named point in the
processing pipeline.  Its behavior depends on the runtime mode:

- Not in eval: emits event via OTel Logger API, returns the original data.
- In eval: injects dependency data for
  ``purpose="input"``, and emits event via OTel Logger API for purpose="output" or "state".
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, Literal, TypeVar

from opentelemetry.sdk._logs import LoggerProvider

from pixie.instrumentation.wrap_log import WrappedData

from .wrap_registry import (
    get_eval_input,
)
from .wrap_serialization import deserialize_wrap_data, serialize_wrap_data

T = TypeVar("T")

logger_provider = LoggerProvider()
_logger = logger_provider.get_logger(__name__)


class WrapRegistryMissError(KeyError):
    """Raised when a wrap(purpose="input") name is not found in the eval registry."""

    def __init__(self, name: str) -> None:
        super().__init__(
            f"wrap(name={name!r}, purpose='input') not found in eval registry. "
            f"Ensure the dataset entry has a value for {name!r} in its input data."
        )
        self.name = name


class WrapTypeMismatchError(TypeError):
    """Raised when deserialized registry value doesn't match expected type."""

    def __init__(self, name: str, expected_type: type, actual_type: type) -> None:
        super().__init__(
            f"wrap(name={name!r}): expected type {expected_type.__name__}, "
            f"got {actual_type.__name__} from registry."
        )
        self.name = name


def _emit_and_return(data: T, name: str, purpose: str, description: str | None) -> T:

    def _emit(val: Any) -> None:
        _logger.emit(
            body=WrappedData(
                name=name,
                purpose=purpose,
                data=serialize_wrap_data(val),
                description=description,
            ).model_dump(mode="json")
        )

    if callable(data):
        original_callable: Callable[..., Any] = data  # type: ignore[assignment,unused-ignore]

        @functools.wraps(original_callable)
        def _capturing_callable(*args: Any, **kwargs: Any) -> Any:
            result = original_callable(*args, **kwargs)
            _emit(result)
            return result

        return _capturing_callable  # type: ignore[return-value]
    else:
        _emit(data)
        return data


def wrap(
    data: T,
    *,
    purpose: Literal["entry", "input", "output", "state"],
    name: str,
    description: str | None = None,
) -> T:
    """Observe *data* at a named wrap point with a specified purpose."""
    is_callable = callable(data)

    input_registry = get_eval_input()

    if input_registry is not None and purpose == "input":
        if name not in input_registry:
            raise WrapRegistryMissError(name)
        deserialized = deserialize_wrap_data(input_registry[name])
        if is_callable:
            # Return a callable that always returns the injected value.
            # Parameters are intentionally ignored — eval mode replaces
            # the original function's computation with the registry value.
            def _injected_callable(*args: Any, **kwargs: Any) -> Any:
                return deserialized

            return _injected_callable  # type: ignore[return-value]
        return deserialized  # type: ignore[no-any-return]
    else:
        return _emit_and_return(data, name, purpose, description)
