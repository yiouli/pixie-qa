# Sync Runnable Event Loop Compatibility

## What Changed

- Fixed sync runnable execution in the eval harness so `run_and_evaluate` provisions a thread-local asyncio event loop when running via `asyncio.to_thread`.
- This prevents runtime failures for sync wrappers that call `asyncio.get_event_loop().run_until_complete(...)` inside `runnable`.
- Added regression coverage for this pattern in eval utility tests.
- Updated docs/specs to describe the compatibility behavior.

## Files Affected

- `pixie/evals/eval_utils.py`
- `tests/pixie/evals/test_eval_utils.py`
- `docs/package.md`
- `specs/evals-harness.md`

## Migration Notes

- No API changes.
- Existing async runnables are unaffected.
- Sync runnables that internally drive async work now execute reliably under `pixie test`.
