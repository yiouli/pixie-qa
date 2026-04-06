# wrap() — Data-Oriented Observation API

## What changed and why

Introduced the `wrap()` function as a data-oriented observation API for
instrumenting LLM pipelines at named data points.  This provides a
mechanism to:

- **Inject test data** during eval runs (dependency injection for inputs)
- **Capture outputs and state** during eval runs (for evaluator assessment)
- **Emit OTel events** during tracing runs (for production observability)

## New modules

| File | Description |
|---|---|
| `pixie/instrumentation/wrap_registry.py` | Context-var registries for input injection and output capture |
| `pixie/instrumentation/wrap_serialization.py` | jsonpickle helpers for serializing/deserializing wrap data |
| `pixie/instrumentation/wrap.py` | `wrap()` function with three operating modes: no-op, tracing, eval |
| `pixie/instrumentation/trace_writer.py` | Thread-safe JSONL trace file writer for wrap events and LLM spans |

## Updated modules

| File | Description |
|---|---|
| `pixie/config.py` | Added `trace_output: str | None` and `tracing_enabled: bool` fields to `PixieConfig`; reads `PIXIE_TRACE_OUTPUT` and `PIXIE_TRACING` env vars |
| `pixie/instrumentation/__init__.py` | Exports `wrap`, `WrapRegistryMissError`, `WrapTypeMismatchError`, registry helpers |
| `pixie/__init__.py` | Re-exports all new `wrap` API symbols |

## New tests

| File | Description |
|---|---|
| `tests/pixie/instrumentation/test_wrap_registry.py` | Input/capture registry get, set, clear operations |
| `tests/pixie/instrumentation/test_wrap_serialization.py` | Serialize/deserialize roundtrips |
| `tests/pixie/instrumentation/test_wrap.py` | All three wrap() modes: no-op, eval (input/output/state/entry), tracing |
| `tests/pixie/test_config_tracing.py` | `tracing_enabled` and `trace_output` config field tests |

## `wrap()` operating modes

1. **No-op** (default): `PIXIE_TRACING` unset and no eval registry active — returns
   `data` unchanged with zero overhead.
2. **Tracing** (`PIXIE_TRACING=1`): emits an OTel span event for each data point.
   Callables are wrapped to emit on invocation.
3. **Eval** (input registry active): injects dependency values for `purpose="input"`,
   captures values to the capture registry for `purpose="output"` and `purpose="state"`.

## `PIXIE_TRACING` environment variable

Set `PIXIE_TRACING=1` to enable tracing mode for `wrap()`.  When unset or `0`,
`wrap()` is a no-op at runtime (eval mode is controlled by the test runner via
the wrap registry, independent of this flag).

## Migration notes

No existing API has changed.  All new symbols are additive.
