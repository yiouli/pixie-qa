# `pixie.wrap` API and Eval Process Redesign

## Overview

This spec defines the implementation of `pixie.wrap()` — a new data-oriented observation API — and the corresponding changes to the eval runner, config, and serialization modules. The `wrap` API replaces the need for manual mocking in run-harness functions and provides a unified mechanism for observing data, injecting synthetic data during evaluation, and capturing output/state.

See also: `what-is-eval.md` in `pixie-qa-skill-development` for conceptual foundations.

---

## 1. The `wrap()` API

### 1.1 Module location

New file: `pixie/instrumentation/wrap.py`

Re-export from `pixie/instrumentation/__init__.py` and `pixie/__init__.py`.

### 1.2 Function signature

```python
from typing import TypeVar, Literal

T = TypeVar("T")

def wrap(
    data: T,
    *,
    purpose: Literal["entry", "input", "output", "state"],
    name: str,
    description: str | None = None,
) -> T:
    """Observe a data value or data-provider function at a point in the processing pipeline.

    ``data`` can be either a plain value or a callable that produces a value.
    In both cases the return type is ``T`` — the caller gets back exactly the
    same type it passed in.  The implementation distinguishes the two cases
    internally: for a callable, the actual observation (OTel event / trace
    write) happens when the returned wrapper is called, not at ``wrap()``
    time; and in eval mode the returned wrapper yields the registry value
    instead of invoking the original function.

    Args:
        data: A data value or a data-provider callable.
        purpose: Classification of the data point:
            - "entry": app input via entry point (user message, request body)
            - "input": data from external dependencies (DB records, API responses)
            - "output": data going out to external systems or users
            - "state": intermediate state for evaluation (routing decisions, etc.)
        name: Unique identifier for this data point. Used as the key in the
            eval registry and in trace logs.
        description: Optional human-readable description of what this data is.

    Returns:
        The original data unchanged (tracing / no-op modes), or the
        registry value (eval mode with purpose="input").  When ``data``
        is callable the return value is also callable with the same
        signature.
    """
```

### 1.3 Behavior modes

**Tracing disabled** (`PIXIE_TRACING` unset or falsy, no eval registry active):

`wrap()` is a **no-op** — returns `data` unchanged (or the original callable unchanged). No OTel events, no serialization, no overhead. This is the default production behavior.

**Tracing enabled** (`PIXIE_TRACING=1`, no eval registry active):

1. If `data` is a plain value (not callable):
   - Serialize the value via jsonpickle
   - Emit an OTel event with attributes: `wrap.name`, `wrap.purpose`, `wrap.description`, `wrap.data` (serialized)
   - Return `data` unchanged

2. If `data` is callable:
   - Return a wrapper function that, when called:
     - Calls the original function with the same args
     - Serializes the result via jsonpickle
     - Emits an OTel event with the result
     - Returns the result

**Eval mode** (registry active — set by test runner, `PIXIE_TRACING` forced off):

The test runner always clears `PIXIE_TRACING` before calling the runnable, regardless of the environment. In eval mode, `wrap()` operates for data injection/capture but does NOT emit OTel events or write to trace files.

1. For `purpose="input"`:
   - Look up `name` in the global registry
   - If found: deserialize the registry value via jsonpickle, return it (or wrap in a function if `data` was callable)
   - If not found: raise `WrapRegistryMissError(name)` with a clear error message

2. For `purpose="entry"`:
   - Same as production mode (entry data comes from the runnable's arguments, not the registry)

3. For `purpose="output"` or `purpose="state"`:
   - Same as production mode (observe and log), but also store the captured value in a capture registry for the test runner to collect after the run

### 1.4 Global registry

New file: `pixie/instrumentation/wrap_registry.py`

```python
from __future__ import annotations
from contextvars import ContextVar
from typing import Any

# Input registry: populated by test runner before each eval run
# Keys are wrap names, values are jsonpickle-serialized strings
_input_registry: ContextVar[dict[str, str] | None] = ContextVar(
    "_input_registry", default=None
)

# Capture registry: populated by wrap() during eval runs for output/state
_capture_registry: ContextVar[dict[str, Any] | None] = ContextVar(
    "_capture_registry", default=None
)


def set_input_registry(registry: dict[str, str]) -> None:
    """Set the input registry for the current eval run context."""
    _input_registry.set(registry)


def get_input_registry() -> dict[str, str] | None:
    """Get the input registry, or None if not in eval mode."""
    return _input_registry.get()


def clear_input_registry() -> None:
    """Clear the input registry after an eval run."""
    _input_registry.set(None)


def get_capture_registry() -> dict[str, Any] | None:
    """Get the capture registry for output/state values."""
    return _capture_registry.get()


def init_capture_registry() -> dict[str, Any]:
    """Initialize and return a fresh capture registry."""
    reg: dict[str, Any] = {}
    _capture_registry.set(reg)
    return reg


def clear_capture_registry() -> None:
    """Clear the capture registry."""
    _capture_registry.set(None)
```

**Why ContextVar**: Eval runs may be concurrent (via asyncio). `ContextVar` ensures each async task has its own registry without cross-contamination.

### 1.5 Error types

New exceptions in `pixie/instrumentation/wrap.py` (or a shared `pixie/errors.py`):

```python
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
```

### 1.6 OTel event emission

`wrap` observations are emitted as **OTel log events** (not spans, since they are point-in-time data captures, not duration-bounded operations).

Use the OTel Events API or span events on the current active span:

```python
from opentelemetry import trace

def _emit_wrap_event(
    name: str,
    purpose: str,
    data_serialized: str,
    description: str | None,
) -> None:
    """Emit an OTel event for a wrap observation."""
    span = trace.get_current_span()
    if span.is_recording():
        span.add_event(
            "pixie.wrap",
            attributes={
                "wrap.name": name,
                "wrap.purpose": purpose,
                "wrap.data": data_serialized,
                **({"wrap.description": description} if description else {}),
            },
        )
```

If no active span exists (wrap called outside of any observed function), create a standalone event using the tracer. Implementation detail — the key requirement is that the event appears in the trace output.

---

## 2. Serialization with jsonpickle

### 2.1 Dependency

Add `jsonpickle` as a runtime dependency in `pyproject.toml`:

```toml
dependencies = [
    # ... existing deps ...
    "jsonpickle>=3.0",
]
```

### 2.2 Serialization module

New file: `pixie/instrumentation/wrap_serialization.py`

```python
from __future__ import annotations
import jsonpickle
from typing import Any


def serialize_wrap_data(data: Any) -> str:
    """Serialize a Python object to a JSON-readable string via jsonpickle.

    The output is human-readable JSON that preserves type information
    for deserialization back to the original Python object.
    """
    return jsonpickle.encode(data, unpicklable=True, indent=2)


def deserialize_wrap_data(data_str: str) -> Any:
    """Deserialize a jsonpickle string back to a Python object."""
    return jsonpickle.decode(data_str)
```

### 2.3 Security consideration

jsonpickle can deserialize arbitrary Python objects, which is a code execution risk. However, in our use case:

- The serialized data in datasets is authored by the coding agent (trusted)
- The deserialization happens locally during eval runs (not in production)
- No untrusted data is ever deserialized

Document this trust boundary clearly in the module docstring.

---

## 3. Trace output to file (`PIXIE_TRACE_OUTPUT`)

### 3.1 Config change

Add to `PixieConfig` in `pixie/config.py`:

```python
@dataclass(frozen=True)
class PixieConfig:
    # ... existing fields ...
    trace_output: str | None = None  # path for JSONL trace file
    tracing_enabled: bool = False    # whether tracing is active
```

Add to `get_config()`:

```python
trace_output=os.environ.get("PIXIE_TRACE_OUTPUT"),
tracing_enabled=_is_truthy_env(os.environ.get("PIXIE_TRACING", "")),
```

### 3.1.1 `PIXIE_TRACING` — tracing enable/disable

New env var `PIXIE_TRACING` controls whether tracing is active:

| Value                                   | Effect                                                                                |
| --------------------------------------- | ------------------------------------------------------------------------------------- |
| Unset or falsy (`""`, `"0"`, `"false"`) | `enable_storage()`, `wrap()`, and `@observe` are no-ops. Zero overhead in production. |
| Truthy (`"1"`, `"true"`, `"yes"`)       | Full tracing: OTel events, trace file output (if `PIXIE_TRACE_OUTPUT` set), storage.  |

The test runner **must** ensure `PIXIE_TRACING` is unset during evaluation regardless of the environment. `wrap()` still operates in eval mode (registry injection/capture) but does not emit OTel events or write trace files.

**Implementation**: `enable_storage()` checks `config.tracing_enabled` and returns immediately if false (no OTel setup, no processors). `wrap()` checks for an active eval registry first (eval mode takes precedence), then checks `tracing_enabled` for trace-mode behavior, and falls back to no-op.

### 3.2 Trace file writer

New file: `pixie/instrumentation/trace_writer.py`

When `trace_output` is configured, a processor writes all `wrap` events and LLM call spans to the specified file in JSONL format.

```python
from __future__ import annotations
import json
import threading
from pathlib import Path
from typing import Any


class TraceFileWriter:
    """Writes wrap events and LLM spans to a JSONL file.

    Thread-safe: uses a lock for file writes.
    """

    def __init__(self, output_path: str) -> None:
        self._path = Path(output_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        # Truncate the file on init
        self._path.write_text("")

    def write_wrap_event(
        self,
        name: str,
        purpose: str,
        data_serialized: str,
        description: str | None,
        trace_id: str | None = None,
        span_id: str | None = None,
    ) -> None:
        """Write a wrap event as a JSONL line."""
        record: dict[str, Any] = {
            "type": "wrap",
            "name": name,
            "purpose": purpose,
            "data": json.loads(data_serialized),  # embed as JSON object, not string
            "description": description,
            "trace_id": trace_id,
            "span_id": span_id,
        }
        self._write_line(record)

    def write_llm_span(self, span_data: dict[str, Any]) -> None:
        """Write an LLM span as a JSONL line."""
        record = {"type": "llm_span", **span_data}
        self._write_line(record)

    def _write_line(self, record: dict[str, Any]) -> None:
        line = json.dumps(record, default=str)
        with self._lock:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
```

### 3.3 Integration with `enable_storage()`

`enable_storage()` first checks `config.tracing_enabled`. If false, it returns immediately (no-op).

When tracing is enabled and `config.trace_output` is set, create a `TraceFileWriter` and pass it to the `LLMSpanProcessor` and `wrap()` function (via a module-level reference or handler registration).

The `wrap()` function checks for an active `TraceFileWriter` and writes events to it in addition to (or instead of) OTel events. The `LLMSpanProcessor.on_end()` also writes LLM spans to the file when a writer is active.

---

## 4. Test runner changes

### 4.1 New runnable contract

The runnable function signature changes from:

```python
# OLD: takes full eval_input, returns eval_output
def run_app(eval_input: dict[str, Any]) -> Any: ...
```

To:

```python
# NEW: takes only entry-point input, returns None
# wrap() handles input injection and output capture
async def run_app(entry_input: dict[str, Any]) -> None: ...
```

### 4.2 Dataset format changes

The dataset JSON format changes to separate entry input from dependency input:

```json
{
  "name": "qa-golden-set",
  "runnable": "pixie_qa/scripts/run_app.py:run_app",
  "evaluators": ["Factuality"],
  "items": [
    {
      "description": "Customer asks about business hours",
      "entry_input": {
        "user_message": "What are your business hours?"
      },
      "dependency_input": {
        "customer_profile": "{jsonpickle-serialized customer profile object}",
        "conversation_history": "{jsonpickle-serialized list}"
      },
      "expected_output": "Should mention Mon-Fri 9am-5pm"
    }
  ]
}
```

**Key changes:**

- `eval_input` splits into `entry_input` (for purpose="entry" wraps) and `dependency_input` (for purpose="input" wraps)
- `dependency_input` values are jsonpickle-serialized strings, keyed by wrap `name`
- `eval_output` is never stored — it's captured at runtime via `wrap(purpose="output")` and `wrap(purpose="state")`

### 4.3 Test runner flow

Update `pixie/cli/test_command.py` and `pixie/evals/dataset_runner.py`:

For each dataset entry:

1. **Ensure `PIXIE_TRACING` is unset** in the current process environment (tracing must be off during eval)
2. **Parse** `entry_input` and `dependency_input` from the dataset item
3. **Initialize** the capture registry (for output/state)
4. **Populate** the input registry with `dependency_input` values (keyed by name, values are the jsonpickle strings)
5. **Resolve** and call the runnable with `entry_input`
6. **Collect** captured output and state from the capture registry
7. **Clear** both registries
8. **Build** an `Evaluable` from captured data:
   - `eval_input` = entry_input + dependency_input (for evaluator context)
   - `eval_output` = captured output values from wrap(purpose="output")
   - `eval_metadata` = captured state values from wrap(purpose="state")
9. **Run** evaluators on the `Evaluable`

### 4.4 Error handling during eval runs

The test runner should catch and report these errors clearly:

| Error                   | Meaning                                        | Message                                                                                     |
| ----------------------- | ---------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `WrapRegistryMissError` | Dataset entry missing a dependency_input value | "Dataset entry is missing input data for wrap point '{name}'. Add it to dependency_input."  |
| `WrapTypeMismatchError` | Deserialized type doesn't match                | "Type mismatch for '{name}': expected {expected}, got {actual}. Check jsonpickle encoding." |
| jsonpickle decode error | Malformed serialized data                      | "Cannot deserialize dependency_input['{name}']: {error}"                                    |

These errors should be reported per-entry (not abort the entire run) so the coding agent can fix multiple issues at once.

### 4.5 Backward compatibility

The old `eval_input` field in dataset JSON should still be accepted for backward compatibility. When present (and `entry_input`/`dependency_input` are absent), the runner falls back to the old behavior: pass `eval_input` directly to the runnable and expect `eval_output` as a return value.

Detection: if the dataset item has `entry_input` or `dependency_input` keys → new mode. Otherwise → legacy mode.

---

## 5. `Evaluable` model changes

### 5.1 New fields on `Evaluable`

The `Evaluable` model in `pixie/storage/evaluable.py` gains optional fields for the new data:

```python
class Evaluable(BaseModel):
    # ... existing fields ...

    # New: captured output data from wrap(purpose="output"), keyed by wrap name
    captured_output: dict[str, JsonValue] | None = None
    # New: captured state data from wrap(purpose="state"), keyed by wrap name
    captured_state: dict[str, JsonValue] | None = None
```

When the test runner builds an `Evaluable` from a new-mode run:

- `eval_input` = the entry_input dict (for evaluator context)
- `eval_output` = primary output value (the first or only `purpose="output"` wrap, or a dict of all if multiple)
- `captured_output` = all `purpose="output"` values
- `captured_state` = all `purpose="state"` values
- `eval_metadata` = includes dependency_input for evaluator context

---

## 6. CLI: trace filtering utility

Add a new CLI subcommand to filter trace JSONL files by purpose:

```bash
uv run pixie trace filter <trace.jsonl> --purpose entry,input
```

This reads the JSONL file and outputs only lines where `purpose` matches one of the specified values. Useful for the coding agent to extract only entry/input events when generating dataset entries.

Implementation: simple filter on the `purpose` field of each JSON line. Output to stdout.

---

## 7. Public API exports

### 7.1 `pixie/__init__.py`

Add `wrap` to the top-level exports:

```python
from pixie.instrumentation import wrap
```

### 7.2 `pixie/instrumentation/__init__.py`

Add to imports and `__all__`:

```python
from .wrap import wrap
```

---

## 8. Implementation plan (ordered)

### Phase 1: Core `wrap` infrastructure

1. Add `jsonpickle` dependency
2. Add `PIXIE_TRACING` and `trace_output` to `PixieConfig`
3. Implement `pixie/instrumentation/wrap_serialization.py` (serialize/deserialize)
4. Implement `pixie/instrumentation/wrap_registry.py` (input/capture registries via ContextVar)
5. Implement `pixie/instrumentation/wrap.py` (the `wrap()` function with 3-mode behavior)
6. Add public API exports
7. Make `enable_storage()` and `@observe` respect `tracing_enabled` flag
8. Tests for all of the above

### Phase 2: Trace output

1. Implement `pixie/instrumentation/trace_writer.py`
2. Integrate trace writer with `enable_storage()` and `wrap()`
3. Integrate trace writer with `LLMSpanProcessor`
4. Add `pixie trace filter` CLI subcommand
5. Tests for trace output

### Phase 3: Test runner changes

1. Update `Evaluable` model with `captured_output` and `captured_state`
2. Update dataset format parsing in `dataset_runner.py`
3. Update test runner flow in `test_command.py` (ensure `PIXIE_TRACING` is unset during eval)
4. Add backward compatibility for old `eval_input` format
5. Tests for runner changes

---

## 9. Files affected

### New files

| File                                                     | Purpose                                   |
| -------------------------------------------------------- | ----------------------------------------- |
| `pixie/instrumentation/wrap.py`                          | `wrap()` function and error types         |
| `pixie/instrumentation/wrap_registry.py`                 | ContextVar-based input/capture registries |
| `pixie/instrumentation/wrap_serialization.py`            | jsonpickle serialize/deserialize helpers  |
| `pixie/instrumentation/trace_writer.py`                  | JSONL trace file writer                   |
| `tests/pixie/instrumentation/test_wrap.py`               | Tests for wrap function                   |
| `tests/pixie/instrumentation/test_wrap_registry.py`      | Tests for registries                      |
| `tests/pixie/instrumentation/test_wrap_serialization.py` | Tests for serialization                   |
| `tests/pixie/instrumentation/test_trace_writer.py`       | Tests for trace file writer               |

### Modified files

| File                                   | Change                                                                           |
| -------------------------------------- | -------------------------------------------------------------------------------- |
| `pyproject.toml`                       | Add `jsonpickle` dependency                                                      |
| `pixie/__init__.py`                    | Export `wrap`                                                                    |
| `pixie/instrumentation/__init__.py`    | Import and export `wrap`                                                         |
| `pixie/config.py`                      | Add `trace_output`, `tracing_enabled` fields and env vars                        |
| `pixie/storage/evaluable.py`           | Add `captured_output`, `captured_state` fields                                   |
| `pixie/evals/dataset_runner.py`        | Support new dataset format with `entry_input`/`dependency_input`                 |
| `pixie/cli/test_command.py`            | New eval run flow with registry setup/teardown, ensure `PIXIE_TRACING` off       |
| `pixie/instrumentation/handlers.py`    | Integrate trace writer when `trace_output` configured; respect `tracing_enabled` |
| `pixie/instrumentation/processor.py`   | Write LLM spans to trace file when writer active; respect `tracing_enabled`      |
| `pixie/instrumentation/observation.py` | Make `@observe` and `start_observation` respect `tracing_enabled`                |
