# Step 1b: Processing Stack & Data Flow — DAG Artifact

Map the complete data flow through the application by producing a **structured DAG JSON file** that represents every important node in the processing pipeline.

---

## What to investigate

### 1. Find where the LLM provider client is called

Locate every place in the codebase where an LLM provider client is invoked (e.g., `openai.ChatCompletion.create()`, `client.chat.completions.create()`, `anthropic.messages.create()`). These are the anchor points for your analysis. For each LLM call site, record:

- The file and function where the call lives
- Which LLM provider/client is used
- The exact arguments being passed (model, messages, tools, etc.)

### 2. Find the common ancestor entry point

Identify the single function that is the common ancestor of all LLM calls — the application's entry point for a single user request. This becomes the **root** of your DAG.

### 3. Track backwards: external data dependencies flowing IN

Starting from each LLM call site, trace **backwards** through the code to find every piece of data that feeds into the LLM prompt:

- **Application inputs**: user messages, queries, uploaded files, config
- **External dependency data**: database lookups (Redis, Postgres), retrieved context (RAG), cache reads, third-party API responses
- **In-code data**: system prompts, tool definitions, prompt-building logic

### 4. Track forwards: external side-effects flowing OUT

Starting from each LLM call site, trace **forwards** to find every side-effect: database writes, API calls, messages sent, file writes.

### 5. Identify intermediate states

Along the paths between input and output, identify intermediate states needed for evaluation: tool call decisions, routing/handoff decisions, retrieval results, branching logic.

### 6. Identify testability seams

Look for abstract base classes, protocols, or constructor-injected backends. These are testability seams — you'll create mock implementations of these interfaces. If there's no clean interface, you'll use `unittest.mock.patch` at the module boundary.

---

## Output: `pixie_qa/02-data-flow.json`

**Write a JSON file** (not markdown) containing a flat array of DAG nodes. Each node represents a significant point in the processing pipeline.

### Node schema

Each node is a JSON object with these fields:

| Field          | Type           | Required | Description                                                                                                        |
| -------------- | -------------- | -------- | ------------------------------------------------------------------------------------------------------------------ |
| `name`         | string         | Yes      | Unique, meaningful lower_snake_case node name (for example, `handle_turn`). This is the node identity.             |
| `code_pointer` | string         | Yes      | **Absolute** file path with function/method name, optionally with line range. See format below.                    |
| `description`  | string         | Yes      | What this node does and why it matters for evaluation.                                                             |
| `parent`       | string or null | No       | Parent node name (`null` or omitted for root).                                                                     |
| `is_llm_call`  | boolean        | No       | Set `true` only if the node represents an LLM provider call. Defaults to `false` when omitted.                     |
| `metadata`     | object         | No       | Additional info: `mock_strategy`, `data_shape`, `credentials_needed`, `eval_relevant`, external system notes, etc. |

### About `is_llm_call`

- Use `is_llm_call: true` for nodes that represent real LLM provider spans.
- Leave it omitted (or `false`) for all other nodes.

### `code_pointer` format

The `code_pointer` field uses **absolute file paths** with a symbol name, and an optional line number range:

- `<absolute_file_path>:<symbol>` — points to a whole function or method. Use this when the entire function represents a single node in the DAG (most common case).
- `<absolute_file_path>:<symbol>:<start_line>:<end_line>` — points to a specific line range within a function. Use this when the function contains an **important intermediate state** — a code fragment that transforms some input into an output that matters for evaluation, but the fragment is embedded inside a larger function rather than being its own function.

**When to use a line range (intermediate states):**

Some functions do multiple important things sequentially. If one of those things produces an intermediate state that your evaluators need to see (e.g., a routing decision, a context assembly step, a tool-call dispatch), but it's not factored into its own function, use a line range to identify that specific fragment. The line range marks the input → output boundary of that intermediate state within the larger function.

Examples of intermediate states that warrant a line range:

- **Routing decision**: lines 51–71 of `main()` decide which agent to hand off to based on user intent — the input is the user message, the output is the selected agent
- **Context assembly**: lines 30–45 of `handle_request()` gather documents from a vector store and format them into a prompt — the input is the query, the output is the assembled context
- **Tool dispatch**: lines 80–95 of `process_turn()` parse the LLM's tool-call response and execute the selected tool — the input is the tool-call JSON, the output is the tool result

If the intermediate state is already its own function, just use the function-level `code_pointer` (no line range needed).

Examples:

- `/home/user/myproject/app.py:handle_turn` — whole function
- `/home/user/myproject/src/agents/llm/openai_llm.py:run_ai_response` — whole function
- `/home/user/myproject/src/agents/agent.py:main:51:71` — lines 51–71 of `main()`, where a routing decision happens

The symbol can be:

- A function name: `my_func` → matches `def my_func` in the file
- A class.method: `MyClass.func` → matches `def func` inside `class MyClass`

### Example

```json
[
  {
    "name": "handle_turn",
    "code_pointer": "/home/user/myproject/src/agents/agent.py:handle_turn",
    "description": "Entry point for a single user request. Takes user message + conversation history, returns agent response.",
    "parent": null,
    "metadata": {
      "data_shape": {
        "input": "str (user message)",
        "output": "str (response text)"
      }
    }
  },
  {
    "name": "load_conversation_history",
    "code_pointer": "/home/user/myproject/src/services/redis_client.py:get_history",
    "description": "Reads conversation history from Redis. Returns list of message dicts.",
    "parent": "handle_turn",
    "metadata": {
      "system": "Redis",
      "data_shape": "list[dict] with role/content keys",
      "mock_strategy": "Provide canned history list",
      "credentials_needed": true
    }
  },
  {
    "name": "run_ai_response",
    "code_pointer": "/home/user/myproject/src/agents/llm/openai_llm.py:run_ai_response",
    "description": "Calls OpenAI API with system prompt + history + user message. Auto-captured by OpenInference.",
    "parent": "handle_turn",
    "is_llm_call": true,
    "metadata": {
      "provider": "OpenAI",
      "model": "gpt-4o-mini"
    }
  },
  {
    "name": "save_conversation_to_redis",
    "code_pointer": "/home/user/myproject/src/services/redis_client.py:save_history",
    "description": "Writes updated conversation history back to Redis after LLM responds.",
    "parent": "handle_turn",
    "metadata": {
      "system": "Redis",
      "eval_relevant": false,
      "mock_strategy": "Capture written data for assertions"
    }
  }
]
```

### Validation checkpoint

After writing `pixie_qa/02-data-flow.json`, validate the DAG:

```bash
uv run pixie dag validate pixie_qa/02-data-flow.json
```

This command:

1. Checks the JSON structure is valid
2. Verifies node names use lower_snake_case
3. Verifies all node names are unique
4. Verifies all parent references exist
5. Checks exactly one root node exists (`parent` is null/omitted)
6. Detects cycles
7. Verifies code_pointer files exist on disk
8. Verifies symbols exist in the referenced files
9. Verifies line number ranges are valid (if present)
10. **Generates a Mermaid diagram** at `pixie_qa/02-data-flow.md` if validation passes

If validation fails, fix the errors and re-run. The error messages are specific — they tell you exactly which node has the problem and what's wrong.

### Also document testability seams

After the DAG JSON is validated, add a brief **testability seams** section at the bottom of the generated `pixie_qa/02-data-flow.md` (the Mermaid file). For each node that reads from or writes to an external system, note the mock interface:

| Dependency node | Interface / module boundary | Mock strategy |
| --------------- | --------------------------- | ------------- |
| ...             | ...                         | ...           |

This section supplements the DAG — the DAG captures _what_ the dependencies are, and this table captures _how_ to mock them.
