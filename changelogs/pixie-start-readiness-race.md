# Pixie Start Readiness Race

## What changed

`pixie start` no longer polls startup readiness through the stale-lock cleanup path while waiting for the detached web server to come up. The wait loop now reads the current `server.lock` value directly and probes `/api/status` without deleting a freshly written lock mid-startup.

This fixes a race where the child process had already started or was about to start serving, but the parent removed the lock too early, reported a timeout, and skipped opening the browser.

## Files affected

- `pixie/web/server.py`
- `tests/pixie/web/test_app.py`
- `frontend/README.md`
- `specs/web-server-lifecycle.md`

## Migration notes

No API changes. `pixie start` and other callers of detached startup now behave more reliably under slow or slightly delayed server startup.
