# Usage Telemetry

## What changed

- Added `pixie.telemetry`, a stdlib-only, fire-and-forget PostHog emitter with
  opt-out support via `PIXIE_NO_TELEMETRY=1`.
- Added anonymous usage events for `pixie test`, `pixie start`, and artifact
  creation batches detected by the file watcher.
- Persisted a stable anonymous install identifier at `<pixie_root>/install_id`
  and updated `pixie init` to ignore that file.
- Documented the privacy disclosure in the root README and added regression
  tests for telemetry persistence, opt-out behavior, CLI hooks, and watcher
  batch deduping.

## Files affected

- Runtime: `pixie/telemetry.py`, `pixie/__init__.py`, `pixie/cli/test_command.py`, `pixie/cli/start_command.py`, `pixie/web/watcher.py`, `pixie/cli/init_command.py`
- Tests: `tests/pixie/test_telemetry.py`, `tests/pixie/cli/test_test_command.py`, `tests/pixie/cli/test_init_command.py`, `tests/pixie/web/test_watcher.py`, `tests/pixie/web/test_app.py`
- Docs: `README.md`, `tests/README.md`, `specs/usage-tracking.md`

## Migration notes

- Set `PIXIE_NO_TELEMETRY=1` in the environment to disable all telemetry.
- Existing CLI output, exit codes, and watcher broadcasts are unchanged.
