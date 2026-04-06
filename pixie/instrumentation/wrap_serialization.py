"""Serialization helpers for wrap() data using jsonpickle.

Security note: jsonpickle can deserialize arbitrary Python objects. In this
codebase, serialized data in datasets is authored by the coding agent (trusted),
deserialization happens locally during eval runs (not in production), and no
untrusted data is ever deserialized.
"""

from __future__ import annotations

from typing import Any

import jsonpickle


def serialize_wrap_data(data: Any) -> str:
    """Serialize a Python object to a jsonpickle JSON string.

    The output is valid JSON but uses jsonpickle's type-metadata format
    (e.g. ``py/object`` keys) rather than plain JSON. This preserves type
    information so that :func:`deserialize_wrap_data` can reconstruct the
    original Python object.
    """
    return jsonpickle.encode(data, unpicklable=True, indent=2)  # type: ignore[no-any-return]


def deserialize_wrap_data(data_str: str) -> Any:
    """Deserialize a jsonpickle string back to a Python object."""
    return jsonpickle.decode(data_str)
