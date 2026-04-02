# Run Harness Example: FastAPI / Web Server with External Services

**When your app is a web server** (FastAPI, Flask, etc.) with external service dependencies (Redis, Twilio, speech services, databases). **This is the most common case** — most production apps are web servers.

**Do NOT call an inner function** like `agent.respond()` directly just because it's simpler. Between the entry point and that inner function, the app does request handling, state management, prompt assembly, routing — all of which is under test. When you call an inner function, you skip all of that and end up reimplementing it in your test. Now your test is testing test code, not app code.

**Approach**: Mock external dependencies, then drive the app through its HTTP/WebSocket interface. Two sub-approaches:

- **Subprocess approach**: Launch the patched server as a subprocess, wait for health, then send HTTP/WebSocket requests with `httpx`. Best when the app has complex startup or uses `uvicorn.run()`.
- **In-process approach**: Use FastAPI's `TestClient` (or `httpx.AsyncClient` with `ASGITransport`) to drive the app in-process. Simpler — no subprocess management, no ports. Best when you can import the `app` object directly.

Both approaches exercise the full request pipeline: routing → middleware → state management → business logic → response assembly.

## Step 1: Identify pluggable interfaces and write mock backends

Look for abstract base classes, protocols, or constructor-injected backends in the codebase. These are the app's testability seams — the places where external services can be swapped out. Create mock implementations that satisfy the interface but don't call external services.

```python
# pixie_qa/scripts/mock_backends.py
from myapp.services.transcription import TranscriptionBackend
from myapp.services.voice_synthesis import SynthesisBackend

class MockTranscriptionBackend(TranscriptionBackend):
    """Decodes UTF-8 text instead of calling real STT service."""
    async def transcribe_chunk(self, audio_data: bytes) -> str | None:
        try:
            return audio_data.decode("utf-8")
        except UnicodeDecodeError:
            return None

class MockSynthesisBackend(SynthesisBackend):
    """Encodes text as bytes instead of calling real TTS service."""
    async def synthesize(self, text: str) -> bytes:
        return text.encode("utf-8")
```

## Step 2: Write the patched server launcher

Monkey-patch the app's module-level dependencies before starting the server:

```python
# pixie_qa/scripts/demo_server.py
import uvicorn
from pixie_qa.scripts.mock_backends import (
    MockTranscriptionBackend,
    MockSynthesisBackend,
)

# Patch module-level backends BEFORE uvicorn imports the ASGI app
import myapp.app as the_app
the_app.transcription_backend = MockTranscriptionBackend()
the_app.synthesis_backend = MockSynthesisBackend()

if __name__ == "__main__":
    uvicorn.run(the_app.app, host="127.0.0.1", port=8000)
```

## Step 3: Write the utility function (subprocess approach)

Launch the server subprocess, wait for health, send real requests, collect responses.

**Starting the server**: Always use `run-with-timeout.sh` to start the server in the background. This avoids issues where background processes get killed between terminal commands.

```bash
# Start the patched server with a 120-second timeout
bash resources/run-with-timeout.sh 120 uv run python -m pixie_qa.scripts.demo_server
sleep 3  # Wait for server readiness
```

Then write `run_app.py` to send requests to the running server:

```python
# pixie_qa/scripts/run_app.py
import httpx
from pixie import enable_storage, observe

BASE_URL = "http://127.0.0.1:8000"

@observe
def run_app(eval_input: dict) -> dict:
    """Send a request to the running server and return the response."""
    enable_storage()
    resp = httpx.post(f"{BASE_URL}/api/chat", json={
        "message": eval_input["user_message"],
    }, timeout=30)
    return resp.json()
```

**Run**: `uv run python -m pixie_qa.scripts.run_app`

## Alternative: In-process with TestClient (simpler)

If the app's `app` object can be imported directly, skip the subprocess and use FastAPI's `TestClient`:

```python
# pixie_qa/scripts/run_app.py
from unittest.mock import patch
from fastapi.testclient import TestClient
from pixie import enable_storage, observe

from pixie_qa.scripts.mock_backends import (
    MockTranscriptionBackend,
    MockSynthesisBackend,
)

@observe
def run_app(eval_input: dict) -> dict:
    """Run the voice agent through its real FastAPI app layer."""
    enable_storage()
    # Patch external dependencies before importing the app
    with patch("myapp.app.transcription_backend", MockTranscriptionBackend()), \
         patch("myapp.app.synthesis_backend", MockSynthesisBackend()), \
         patch("myapp.app.call_state_store", MockCallStateStore()):

        from myapp.app import app
        client = TestClient(app)

        # Drive through the real HTTP/WebSocket endpoints
        resp = client.post("/api/chat", json={
            "message": eval_input["user_message"],
            "call_sid": eval_input.get("call_sid", "test-call-001"),
        })
        return {"response": resp.json()["response"]}
```

This approach is simpler (no subprocess, no port management) and equally valid. Both approaches exercise the full request pipeline.

**Run**: `uv run python -m pixie_qa.scripts.run_app`

---

## Gotcha: FastAPI TestClient + Database Connections

When using `TestClient` with a FastAPI app that manages database connections in its `lifespan`, you'll hit `sqlite3.ProgrammingError: Cannot operate on a closed database` if you're not careful. This happens because:

1. **TestClient runs lifespan startup/shutdown**: When you enter `with TestClient(app) as client:`, the lifespan starts (opening the DB). When you exit, the lifespan shuts down (**closing the DB**).
2. **In-memory SQLite dies on close**: An in-memory `sqlite3.connect(":memory:")` connection destroys the database when closed — there's no file to reconnect to.

### The fix: initialize once at module level, use NonClosingConnection

Create the DB and TestClient **once at module level** instead of per-call. Wrap the connection so `close()` is a no-op. This solves both the closed-DB problem and the concurrency-safety problem (see next section):

```python
class _NonClosingConnection:
    """Wraps a sqlite3.Connection, forwarding everything except close()."""
    def __init__(self, real_conn: sqlite3.Connection) -> None:
        self._real = real_conn
    def __getattr__(self, name: str):
        return getattr(self._real, name)
    def close(self) -> None:
        pass  # Prevent lifespan teardown from killing our mock DB
```

See the next section ("Concurrency-safe harness") for the complete pattern that combines `_NonClosingConnection` with module-level initialization.

## Concurrency-safe harness — initialize once, run concurrently

`assert_dataset_pass` runs the runnable concurrently for multiple dataset items. Your `run_app` function **must be safe to call from multiple threads at the same time**. A common mistake is to wrap the entire function in a `threading.Lock()` — this serializes all runs and makes tests extremely slow (e.g., 5 items × 7s each = 35s serial, vs 9s with 4-way concurrency).

**❌ WRONG — global lock serializes all runs:**

```python
_run_lock = threading.Lock()

def run_app(eval_input: dict) -> dict:
    with _run_lock:  # ← Every call waits for all previous ones to finish
        ...
```

**✅ CORRECT — initialize once, run concurrently:**

Most web apps use per-session state (keyed by session ID, call ID, etc.) that is naturally isolated across concurrent calls. The right pattern is:

1. **Initialize the app ONCE at module level** — create the TestClient, DB, and services once
2. **Each `run_app` call reuses the shared client** — the app's per-session state (keyed by unique ID) provides isolation
3. **No lock needed** — concurrent calls use different session IDs and don't interfere

```python
# pixie_qa/scripts/run_app.py
import sqlite3
from fastapi.testclient import TestClient
from unittest.mock import patch
from pixie import enable_storage

from src.services.db import init_db, seed_data


class _NonClosingConnection:
    """Wraps sqlite3.Connection, making close() a no-op."""
    def __init__(self, real_conn: sqlite3.Connection) -> None:
        self._real = real_conn
    def __getattr__(self, name: str):
        return getattr(self._real, name)
    def close(self) -> None:
        pass


# ── Module-level setup: initialize app ONCE ────────────────────────────────
# Create a shared in-memory DB with seed data (read-only reference data).
# The app's per-session stores (keyed by call_sid, session_id, etc.)
# provide natural isolation between concurrent runs.
_conn = sqlite3.connect(":memory:", check_same_thread=False)
_conn.row_factory = sqlite3.Row
init_db(_conn)
seed_data(_conn)
_safe_conn = _NonClosingConnection(_conn)

# Patch the connection getter BEFORE importing the app so the lifespan
# picks it up, then create a single long‑lived TestClient.
with patch("app.get_connection", return_value=_safe_conn):
    from app import app
    _client = TestClient(app).__enter__()


def run_app(eval_input: dict) -> dict:
    """Run a single eval scenario — safe to call concurrently.

    Each call gets a unique session/call ID from the app, so concurrent
    calls never share mutable state.
    """
    enable_storage()

    # Drive through real endpoints — app assigns unique IDs internally
    resp = _client.post("/start-call", json={...})
    call_sid = resp.json()["call_sid"]
    for msg in eval_input["turns"]:
        resp = _client.post("/chat", json={"call_sid": call_sid, "message": msg})
    return resp.json()
```

**Why this works:**

- The DB holds reference data (agent configs, customer records) — read-only, safe to share
- The app's in-memory stores (`CallStateStore`, `ActiveStreamStore`) are dicts keyed by `call_sid` — each call creates its own entry
- The LLM service is stateless — it reads from the stores per-call
- `TestClient` can handle concurrent requests to the same app

**When does this pattern apply?**

- The app manages per-session/per-call state keyed by unique IDs (most web apps)
- The shared DB contains only seed/config data that is read, not mutated by test calls
- The app services are stateless orchestrators that read/write to keyed stores

**When you truly cannot avoid serialization** (rare — e.g., app writes to a shared file, uses global counters):
Only then fall back to a lock, but wrap the **minimum** scope — just the racy operation, not the entire `run_app` body.
