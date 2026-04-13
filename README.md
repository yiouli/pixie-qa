# pixie-qa

Eval-driven development for Python LLM applications.

pixie-qa ships two complementary tools:

- **`eval-driven-dev` agent skill** — guides a coding agent through the full eval-driven development loop: instrument → capture → build dataset → test → investigate → iterate.
- **`pixie-qa` Python package** — the runtime: `wrap()` for data-boundary instrumentation, `Runnable` for dataset-driven test execution, built-in and custom evaluators, and the `pixie` CLI.

## Agent Skill

### Install

```bash
npx skills add yiouli/pixie-qa
```

### Usage

Open a conversation with your coding agent and say something like:

> "set up QA for my app"

The agent follows a six-step workflow:

1. **Understand the app** — entry point, execution flow, expected behaviors
2. **Instrument with `wrap()`** — mark data boundaries in the production code path
3. **Define evaluators** — map quality criteria to built-in or custom evaluators
4. **Build a dataset** — diverse representative scenarios in JSON
5. **Run `pixie test`** — real pass/fail scores for every scenario
6. **Investigate & iterate** — root-cause failures and fix

## Python Package

### Install

```bash
pip install pixie-qa
# with an LLM provider auto-instrumentor:
pip install "pixie-qa[openai]"   # openai | anthropic | langchain | google | dspy | all
```

### `wrap()` — instrument data boundaries

Call `wrap()` at data boundaries in your application code. At test time, `wrap(purpose="input")` values are injected from the dataset; `wrap(purpose="output")` values are captured and scored by evaluators.

```python
from pixie import wrap

db_result = wrap(fetch_from_db(user_id), purpose="input", name="db_result")
response   = wrap(generate_response(db_result), purpose="output", name="response")
```

| Purpose    | Meaning                                                |
| ---------- | ------------------------------------------------------ |
| `"input"`  | External data fed into the LLM (injected at test time) |
| `"output"` | Final or intermediate output to evaluate               |
| `"state"`  | Intermediate state captured for debugging              |

### `Runnable` — run the app against each dataset entry

Implement the `Runnable` protocol so `pixie test` and `pixie trace` know how to run your app:

```python
from pydantic import BaseModel
import pixie

class MyArgs(BaseModel):
    user_id: str
    message: str

class MyAppRunnable(pixie.Runnable[MyArgs]):
    @classmethod
    def create(cls) -> "MyAppRunnable":
        return cls()

    async def setup(self) -> None:
        pass  # one-time initialization before entries run

    async def run(self, args: MyArgs) -> None:
        await my_app.handle(args.user_id, args.message)

    async def teardown(self) -> None:
        pass  # one-time cleanup after all entries finish
```

`run()` is called concurrently for all dataset entries — protect shared mutable state with `asyncio.Semaphore` or `asyncio.Lock` if needed.

### Dataset JSON format

```json
{
  "runnable": "pixie_qa/scripts/run_app.py:MyAppRunnable",
  "evaluators": ["Factuality"],
  "entries": [
    {
      "input_data": { "user_id": "u1", "message": "What is my balance?" },
      "test_case": {
        "eval_input": [
          {
            "purpose": "input",
            "name": "db_result",
            "data": { "balance": 120.5 }
          }
        ],
        "expectation": "Your current balance is $120.50.",
        "description": "basic balance query"
      }
    }
  ]
}
```

Use `pixie trace` + `pixie format` to capture real traces and turn them into dataset entries with the correct data shapes.

### Evaluators

| Evaluator              | Task                                             |
| ---------------------- | ------------------------------------------------ |
| `Factuality`           | LLM-as-judge factual accuracy                    |
| `ClosedQA`             | LLM-as-judge Q&A with reference answer           |
| `AnswerCorrectness`    | RAGAS combined factual + semantic similarity     |
| `EmbeddingSimilarity`  | Cosine similarity between output and expectation |
| `ExactMatch`           | Deterministic exact string match                 |
| `create_llm_evaluator` | Custom prompt-based LLM-as-judge                 |

Full evaluator list: [docs/pixie/index.md](docs/pixie/index.md)

### CLI reference

| Command                                         | Description                                   |
| ----------------------------------------------- | --------------------------------------------- |
| `pixie test [path]`                             | Run eval tests; open scorecard in browser     |
| `pixie trace --runnable R --input I --output O` | Run a Runnable, capture trace to JSONL        |
| `pixie format --input I --output O`             | Convert a trace JSONL to a dataset entry JSON |
| `pixie init [root]`                             | Scaffold the `pixie_qa/` working directory    |
| `pixie start [root]`                            | Launch the web UI at `http://localhost:7118`  |

## Web UI

View all eval artifacts (results, datasets, markdown docs) in a live-updating local web UI:

```bash
pixie start              # initializes pixie_qa/ (if needed) and opens http://localhost:7118
pixie start my_dir       # use a custom artifact root
pixie init               # scaffolds pixie_qa/ without starting the server
```

Changes to artifacts are pushed to the browser in real time via SSE.

## Configuration

Pixie reads configuration from environment variables and a local `.env` file. Existing process env vars take priority over `.env` values.

| Variable                   | Description                                    |
| -------------------------- | ---------------------------------------------- |
| `PIXIE_ROOT`               | Root directory for all generated artefacts     |
| `PIXIE_RATE_LIMIT_ENABLED` | `true` to enable evaluator throttling          |
| `PIXIE_RATE_LIMIT_RPS`     | Max requests per second for LLM-as-judge calls |
| `PIXIE_RATE_LIMIT_RPM`     | Max requests per minute                        |
| `PIXIE_RATE_LIMIT_TPS`     | Max tokens per second                          |
| `PIXIE_RATE_LIMIT_TPM`     | Max tokens per minute                          |
