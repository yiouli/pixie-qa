# Step 2: Instrument and observe a real run

> For a quick lookup of imports, CLI commands, and key concepts, see `quick-reference.md`.

**Why this step**: You need to see the actual data flowing through the app before you can build anything. This step produces a reference trace that shows the exact data shapes you'll use for datasets and evaluators.

**This is a normal app run with instrumentation — no mocks, no patches.**

## prerequisite: enable instrumentation

Add `enable_storage()` at the application's startup point (inside `main()`, a FastAPI lifespan, or similar — **never at module level**). This function enables OTel data emission from LLM provider clients, and subscribes an event processor to save emitted Otel data into a local sqlite database.

## 2a. Add instrumentation — use the DAG

Open your DAG file (`pixie_qa/02-data-flow.json`). For each node that does NOT have `is_llm_call: true`:

1. Go to the file and function specified by the node's `code_pointer`
2. **If the `code_pointer` has no line number range**: decorate the function with `@observe(name="<node_name>")`
3. **If the `code_pointer` has a line number range** (e.g., `/path/to/file.py:func:51:71`): wrap that code section with `start_observation(input=..., name="<node_name>")` inside the existing function

The `name` parameter MUST be the exact `name` of the corresponding DAG node.

Nodes with `is_llm_call: true` are auto-captured by OpenInference — do NOT add `@observe` to them.

### @observe example

```python
# ✅ Decorating the existing production function
from pixie import observe

@observe(name="answer_question")
def answer_question(question: str, context: str) -> str:  # existing function
    ...  # existing code, unchanged
```

```python
# ✅ Decorating a class method (works exactly the same way)
from pixie import observe

class OpenAIAgent:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = model

    @observe(name="openai_agent_respond")
    def respond(self, user_message: str, conversation_history: list | None = None) -> str:
        # existing code, unchanged — @observe handles `self` automatically
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})
        response = self.client.chat.completions.create(model=self.model, messages=messages)
        return response.choices[0].message.content or ""
```

### start_observation example

```python
# ✅ Context manager inside an existing function
from pixie import start_observation

async def main():  # existing function
    ...
    with start_observation(input={"user_input": user_input}, name="handle_turn") as obs:
        result = await Runner.run(current_agent, input_items, context=context)
        # ... existing response handling ...
        obs.set_output(response_text)
    ...
```

### Anti-patterns

```python
# ❌ WRONG — creating a new wrapper function
@observe(name="run_for_eval")
async def run_for_eval(user_messages: list[str]) -> str:
    # Duplicates what main() does — creates a separate code path
    ...

# ✅ CORRECT — decorate the existing function directly
```

```python
# ❌ WRONG — creating a wrapper method instead of decorating the existing one
class OpenAIAgent:
    def respond(self, user_message, conversation_history=None):
        return self._respond_observed(...)

    @observe
    def _respond_observed(self, args):
        ...

# ✅ CORRECT — decorate the existing method
class OpenAIAgent:
    @observe(name="openai_agent_respond")
    def respond(self, user_message, conversation_history=None):
        ...  # existing code, unchanged
```

```python
# ❌ WRONG — bypassing the app by calling the LLM directly
@observe(name="agent_answer_question")
def answer_question(question: str) -> str:
    response = client.responses.create(model="gpt-4.1", input=[...])
    return response.output_text

# ✅ CORRECT — import and call the app's own function
```

### Rules

- **Import rule**: All pixie symbols are importable from `from pixie import ...`. Never import from submodules.
- **Never change the function's interface** (arguments, return type, behavior). The instrumentation is purely additive.
- After instrumentation, call `flush()` at the end of runs to make sure all spans are written.
- For interactive apps (CLI loops, chat interfaces), instrument the **per-turn processing** function.

## 2b. Run the app and verify the trace

Run the app normally — with real external dependencies — to produce a reference trace. Do NOT mock or patch anything.

If the app can't run without infrastructure you don't have, use the simplest approach to get it running (local Docker, test account, or ask the user).

### Starting a web server for trace capture

If the app is a web server (FastAPI, Flask, etc.), you need to start it in the background, send a request, then verify the trace. **Always use the `run-with-timeout.sh` script** to start background servers — never start them with bare `&` or `nohup` directly, because background processes may be killed between terminal commands.

```bash
# Start the server with a 120-second timeout (auto-killed after that)
bash resources/run-with-timeout.sh 120 uv run uvicorn app:app --host 127.0.0.1 --port 8000

# Wait for the server to be ready
sleep 3

# Send a test request to produce a trace
curl -X POST http://127.0.0.1:8000/your-endpoint -H 'Content-Type: application/json' -d '{...}'
```

The script starts the command with `nohup`, prints the PID, and spawns a watchdog that kills the process after the timeout. You don't need to manually stop it — it will be cleaned up automatically.

**Verify the trace:**

```bash
uv run pixie trace verify
```

If it reports issues, fix them according to the error messages and re-run.

## 2c. Validate the trace against the DAG

```bash
uv run pixie dag check-trace pixie_qa/02-data-flow.json
```

This checks that every DAG node has a matching span in the trace. **Every non-LLM node must appear in this single trace.** If a node is missing, either:

1. The function at `code_pointer` is not decorated with `@observe(name="<node_name>")`
2. The function was not called during the trace run

If you have conditional branches (e.g., `end_call` vs `transfer_call`), go back to Step 1b and simplify: merge mutually exclusive branches into a single dispatcher node so all nodes are exercisable in one trace.

If it reports errors, fix them according to the error messages and re-run.

## 2d. Document the reference trace

Once both `pixie trace verify` and `pixie dag check-trace` pass, use `pixie trace last` to inspect the full trace details and document the eval_input/eval_output shapes.

## Output: `pixie_qa/04-reference-trace.md`

Document the reference trace:

1. **eval_input shape** — field names, types, nesting from the root span's input
2. **eval_output shape** — field names, types, nesting from the root span's output
3. **External data (inbound)** — what the app read from databases/APIs/caches (shapes and realistic values)
4. **Side-effects (outbound)** — what the app wrote to external systems
5. **Completeness check** — for each eval criterion from Step 1, confirm the trace contains the data needed to evaluate it

### Template

```markdown
# Reference Trace Analysis

## eval_input shape

<field names, types, nesting — from the @observe-decorated entry point's input>

## eval_output shape

<field names, types, nesting — from the @observe-decorated entry point's output>

## External data (inbound)

| Source | Data shape | Realistic value ranges |
| ------ | ---------- | ---------------------- |
| ...    | ...        | ...                    |

## Side-effects (outbound)

| Target | Data written | How to capture in mock |
| ------ | ------------ | ---------------------- |
| ...    | ...          | ...                    |

## Intermediate states captured

| Span name | Data captured | Eval criteria it supports |
| --------- | ------------- | ------------------------- |
| ...       | ...           | ...                       |

## Instrumentation completeness check

| Eval criterion | Data needed | Present in trace? | Fix needed? |
| -------------- | ----------- | ----------------- | ----------- |
| ...            | ...         | ✓ / ✗             | ...         |
```
