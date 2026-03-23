# @observe: Strip `self` and `cls` from captured input

## What changed

The `@observe` decorator now automatically removes `self` and `cls` from the
captured function arguments before serialization. Previously, decorating a
method with `@observe` would serialize the entire instance (including API keys,
client objects, and other sensitive state) into `eval_input` via jsonpickle.

## Files affected

- `pixie/instrumentation/observation.py` — `sync_wrapper` and `async_wrapper`
  now pop `self`/`cls` from `bound.arguments` before calling `_serialize()`.
- `tests/pixie/instrumentation/test_observation.py` — Two new tests:
  `test_self_excluded_from_input` and `test_cls_excluded_from_input`.

## Migration notes

No API changes. This is a backward-compatible fix. Existing `@observe` usage on
functions (not methods) is unaffected. Methods that previously leaked `self` into
`eval_input` will now produce cleaner, smaller input data containing only the
semantic arguments.
