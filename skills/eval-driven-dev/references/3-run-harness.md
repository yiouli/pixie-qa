# Step 3: Write a utility function to run the full app end-to-end

**Why this step**: You need a function that test cases can call. Given an eval_input (app input + mock data for external dependencies), it starts the real application with external dependencies patched, sends the input through the app's real entry point, and returns the eval_output (app response + captured side-effects).

## The contract

```text
run_app(eval_input) → eval_output
```

- **eval_input** = application input (what the user sends) + data from external dependencies (what databases/APIs would return)
- **eval_output** = application output (what the user sees) + captured side-effects (what the app wrote to external systems, captured by mocks) + captured intermediate states (tool calls, routing decisions, etc., captured by instrumentation)

## How to implement

1. **Patch external dependencies** — use the mocking plan from `pixie_qa/02-data-flow.md`. For each node that reads from or writes to an external system, either inject a mock implementation of its interface (cleanest) or `unittest.mock.patch` the module-level client. The mock returns data from eval_input and captures side-effects for eval_output.

   **Do NOT mock the LLM provider** (OpenAI, Anthropic, etc.). The entire point of this QA setup is to evaluate the LLM's actual behavior — its responses, tool-call decisions, and output quality. Mocking the LLM makes the tests tautological (you'd be testing your own mock responses). The LLM call must go to the real API. Only external data dependencies (databases, caches, third-party APIs that are _not_ the LLM) get mocked.

2. **Call the app through its real entry point** — the same way a real user or client would invoke it. Base on how the app runs: if it's a web server (FastAPI, Flask), use `TestClient` or HTTP requests. If it's a CLI, use subprocess. If it's a standalone function with no server or middleware, import and call it directly.

   **Starting web servers**: If you need to start a server process (for the subprocess approach), always use `run-with-timeout.sh` to start it in the background — never use bare `&` or `nohup` directly. See the FastAPI example file for the pattern.

   **TestClient + database gotcha**: If the app manages DB connections in its FastAPI lifespan (common pattern: `_conn = get_connection()` in startup, `_conn.close()` in shutdown), the TestClient's lifespan teardown will close your mock connection. Read the "Gotcha: FastAPI TestClient + Database Connections" section below for the fix (wrap the connection to prevent lifespan from closing it).

   **Concurrency — critical**: `assert_dataset_pass` calls `run_app` concurrently for multiple dataset items. Your harness **must be concurrency-safe**. Do NOT wrap the entire function in a `threading.Lock()` — this serializes all runs and makes tests extremely slow. Instead, initialize the app (TestClient, DB, services) **once at module level** and let each `run_app` call reuse the shared client. The app's per-session state (keyed by call_sid, session_id, etc.) provides natural isolation. Read the "Concurrency-safe harness" section below for the pattern.

3. **Collect the response** — the app's output becomes eval_output, along with any side-effects captured by mock objects.

**Do NOT call an inner function** like `agent.respond()` directly just because it's simpler. The whole point is to test the app's real code path — request handling, state management, prompt assembly, routing. When you call an inner function directly, you skip all of that, and the test has to reimplement it. Now you're testing test code, not app code.

## Output: `pixie_qa/scripts/run_app.py`

## Verify

Take the eval_input from your Step 2 reference trace (`pixie_qa/04-reference-trace.md`) and feed it to the utility function. The outputs won't match word-for-word (non-deterministic), but verify:

- **Same structure** — same fields present, same types, same nesting
- **Same code path** — same routing decisions, same intermediate states captured
- **Sensible values** — eval_output fields have real, meaningful data (not null, not empty, not error messages)

**If it fails after two attempts**, stop and ask the user for help.

---

## Example by app type

Base on how the application runs, read the corresponding example file for implementation guidance:

| App type                            | Entry point             | Example file                                                  |
| ----------------------------------- | ----------------------- | ------------------------------------------------------------- |
| **Web server** (FastAPI, Flask)     | HTTP/WebSocket endpoint | Read `references/run-harness-examples/fastapi-web-server.md`  |
| **CLI application**                 | Command-line invocation | Read `references/run-harness-examples/cli-app.md`             |
| **Standalone function** (no server) | Python function         | Read `references/run-harness-examples/standalone-function.md` |

Read **only** the example file that matches your app type — do not read the others.

For `enable_storage()` and `observe` API details, see `pixie-api.md` (Instrumentation API section).

**Do NOT call an inner function** like `agent.respond()` directly just because it's simpler. Between the entry point and that inner function, the app does request handling, state management, prompt assembly, routing — all of which is under test. When you call an inner function, you skip all of that and end up reimplementing it in your test. Now your test is testing test code, not app code.

Mock only external dependencies (databases, speech services, third-party APIs) — everything you identified and planned in Step 1.

---

## Key Rules

1. **Always call through the real entry point** — the same way a real user or client would
2. **Mock only external dependencies** — the ones you identified in Step 1
3. **Make `run_app` concurrency-safe** — `assert_dataset_pass` calls it concurrently; never use a global lock unless absolutely unavoidable
4. **Use `uv run python -m <module>`** to run scripts — never `python <path>`
5. **Add `enable_storage()` and `@observe`** in the utility function so traces are captured
6. **After running, verify traces**: `uv run pixie trace list` then `uv run pixie trace show <trace_id> --verbose`
