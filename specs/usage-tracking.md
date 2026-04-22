# Spec: Usage Telemetry for pixie-qa

## Goal

Add lightweight, fire-and-forget usage telemetry to the `pixie-qa` Python package so we can
see real usage time series (daily active installs, command volume, artifact changes) via PostHog.

---

## Constraints

- **Zero impact on CLI behavior** — telemetry must never slow down, error out, or change the
  output of any command or the file watcher
- **No new runtime dependencies** — use stdlib only (`urllib`, `threading`, `json`, `uuid`, `os`)
- **Opt-out supported** — respect `PIXIE_NO_TELEMETRY=1` env var
- **Anonymous** — no PII, no usernames, no information of the project, Stable per-machine ID only

---

## New File: `pixie/telemetry.py`

Create this file from scratch.

```python
"""pixie.telemetry — anonymous usage telemetry.

Sends lightweight fire-and-forget events to PostHog so we can understand
real-world usage patterns. No personal data is ever collected.

Set PIXIE_NO_TELEMETRY=1 to opt out.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.request
import uuid

POSTHOG_ENDPOINT = "https://us.i.posthog.com/capture/"
POSTHOG_API_KEY = "phc_uvoRufYTVrwBBh9Jkf4LhQQq4KDRFiNR78vhg8ME8NmK"


def _get_install_id() -> str:
    """Return a stable, anonymous, per-machine ID.

    Generated once and persisted to <pixie_root>/install_id.
    Never raises — returns "unknown" on any failure.
    """
    try:
        from pixie.config import get_config
        install_id_file = os.path.join(get_config().root, "install_id")
        os.makedirs(os.path.dirname(install_id_file), exist_ok=True)
        if os.path.exists(install_id_file):
            return open(install_id_file).read().strip()
        iid = str(uuid.uuid4())
        open(install_id_file, "w").write(iid)
        return iid
    except Exception:
        return "unknown"


def emit(event: str, properties: dict = {}) -> None:
    """Emit an anonymous usage event to PostHog.

    - Runs in a daemon thread — never blocks the caller
    - Silently swallows all errors
    - No-ops if PIXIE_NO_TELEMETRY is set
    """
    if os.environ.get("PIXIE_NO_TELEMETRY"):
        return

    payload = json.dumps({
        "api_key": POSTHOG_API_KEY,
        "event": event,
        "distinct_id": _get_install_id(),
        "properties": properties,
    }).encode()

    def _send() -> None:
        try:
            req = urllib.request.Request(
                POSTHOG_ENDPOINT,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=3)
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()
```

---

## Call Site 1: `pixie/cli/test_command.py`

In `main()`, after `configure_rate_limits_from_config()` and before `asyncio.run(...)`.

```python
from pixie.telemetry import emit
from pixie import __version__

# add after configure_rate_limits_from_config(), before asyncio.run(...)
emit("pixie_test", {"version": __version__})
```

---

## Call Site 2: `pixie/cli/start_command.py`

In `start()`, as the first statement of the function body before any other logic.

```python
from pixie.telemetry import emit
from pixie import __version__

def start(root: str | None = None, *, tab: str | None = None, item_id: str | None = None) -> int:
    emit("pixie_start", {"version": __version__})
    # ... rest of existing function unchanged
```

---

## Call Site 3: `pixie/web/watcher.py`

In `watch_artifacts()`, emit `pixie_artifact_changed` for each relevant artifact change detected
by the watcher. Include the root-relative artifact path and a normalized change type so PostHog
can distinguish creates, updates, and deletes.

Add the following block inside the `async for changes in awatch(root_path):` loop, after
`relevant_changes` is built and before the SSE broadcast calls:

```python
from pixie.telemetry import emit
from pixie import __version__

for change in relevant_changes:
    emit(
        "pixie_artifact_changed",
        {
            "version": __version__,
            "change_type": change_type,
            "artifact_path": change["path"],
        },
    )
```

Import `emit` and `__version__` at the top of `watcher.py` alongside the existing imports.
Use a lazy import inside the function body only if circular import issues arise (check first).

---

## PostHog Setup (manual step, not code)

1. Sign up at <https://posthog.com> → create a project
2. Copy the **Project API Key** (format: `phc_xxxxxxxxxxxx`)
3. Replace `<REPLACE_WITH_POSTHOG_PROJECT_API_KEY>` in `pixie/telemetry.py`
4. The key is safe to commit — it is a write-only ingest key, not a secret

---

## Change to `pixie/cli/init_command.py`

Add `install_id` to `_GITIGNORE_CONTENT` so it is never accidentally committed:

```python
_GITIGNORE_CONTENT = """\
server.lock
server.log
install_id

# remove this if you want to keep the results in source control
results/**
"""
```

---

## README Update

Add a brief disclosure (e.g. under a "Privacy" section):

```markdown
## Privacy

pixie-qa records anonymous usage events to understand how the tool is used in practice.
Artifact-change events include the change type and the artifact path relative to the
pixie root. No personal data, file contents, absolute paths, or project root names are
collected.

To opt out:

    PIXIE_NO_TELEMETRY=1 pixie test
```

---

## What We Do NOT Record (explicitly out of scope)

- Usernames, emails, hostnames, or any PII
- Absolute file paths, project root names, file contents, or eval content
- Errors or stack traces
- Any properties that require reading user files or environment beyond `__version__`

---

## Acceptance Criteria

- [ ] `pixie test` emits a `pixie_test` event with `version` property
- [ ] `pixie start` emits a `pixie_start` event with `version` property
- [ ] Each relevant artifact change emits a `pixie_artifact_changed` event
- [ ] `pixie_artifact_changed` includes `version`, `change_type`, and `artifact_path`
- [ ] `PIXIE_NO_TELEMETRY=1` suppresses all three event types
- [ ] CLI behavior, output, and exit codes are identical with or without telemetry
- [ ] File watcher behavior and SSE broadcast timing are unchanged
- [ ] No new packages added to `pyproject.toml` dependencies
- [ ] `<pixie_root>/install_id` is created on first run and reused on subsequent runs
- [ ] `install_id` is listed in the `.gitignore` written by `pixie init`
- [ ] Events visible in PostHog dashboard within ~30 seconds of the triggering action
