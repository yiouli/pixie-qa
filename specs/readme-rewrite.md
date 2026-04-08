# README Rewrite Spec

## Why

The existing README is stale. It references the old `qa-eval` skill name, omits the
full CLI (`pixie trace`, `pixie format`, `pixie analyze`), does not explain the
eval-driven development workflow, and does not mention the `wrap()` / `Runnable` /
dataset-JSON API that the package actually exposes.

## What the README must cover

### 1. Tagline

One-sentence description: eval-driven development for Python LLM applications.

### 2. Two-tool overview

pixie-qa ships two complementary tools:

- **`eval-driven-dev` agent skill** — guides a coding agent through the full
  eval-driven development loop (instrument → capture → build dataset → test →
  investigate → iterate).
- **`pixie-qa` Python package** — the runtime: `wrap()` for data-boundary
  instrumentation, `Runnable` for dataset-driven test execution, built-in and
  custom evaluators, and the `pixie` CLI.

### 3. Agent skill section

#### Install

```bash
npx skills add yiouli/pixie-qa
```

#### Usage

Ask the coding agent in natural language, e.g.:

> "set up QA for my app"

The agent follows a structured six-step workflow:

1. Understand the app — entry point, execution flow, expected behaviors
2. Instrument with `wrap()` — mark data boundaries in the production code path
3. Define evaluators — map quality criteria to built-in or custom evaluators
4. Build a dataset — diverse representative scenarios in JSON
5. Run `pixie test` — real pass/fail scores for every scenario
6. Investigate & iterate — root-cause failures and fix

### 4. Python package section

#### Install

```bash
pip install pixie-qa
# or with an LLM provider extra:
pip install "pixie-qa[openai]"   # openai, anthropic, langchain, google, dspy, all
```

#### `wrap()` — instrument data boundaries

```python
from pixie import wrap

db_result = wrap(fetch_from_db(user_id), purpose="input", name="db_result")
response   = wrap(generate_response(db_result), purpose="output", name="response")
```

Three purpose values:

| Purpose    | Meaning                                              |
| ---------- | ---------------------------------------------------- |
| `"input"`  | External data fed into the LLM (injected at test time) |
| `"output"` | Final or intermediate output to evaluate             |
| `"state"`  | Intermediate state captured for debugging            |

#### `Runnable` — run the app against each dataset entry

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

    async def run(self, args: MyArgs) -> None:
        await my_app.handle(args.user_id, args.message)
```

#### Dataset JSON format

```json
{
  "runnable": "pixie_qa/scripts/run_app.py:MyAppRunnable",
  "evaluators": ["Factuality"],
  "entries": [
    {
      "entry_kwargs": { "user_id": "u1", "message": "What is my balance?" },
      "test_case": {
        "eval_input": [
          { "purpose": "input", "name": "db_result", "data": { "balance": 120.5 } }
        ],
        "expectation": "Your current balance is $120.50.",
        "description": "basic balance query"
      }
    }
  ]
}
```

#### Built-in evaluators

Common evaluators (all from `pixie` or `pixie.eval.scorers`):

| Evaluator             | Task                                               |
| --------------------- | -------------------------------------------------- |
| `Factuality`          | LLM-as-judge factual accuracy                     |
| `ClosedQA`            | LLM-as-judge Q&A with reference answer            |
| `AnswerCorrectness`   | RAGAS combined factual + semantic similarity       |
| `EmbeddingSimilarity` | Cosine similarity of output and expectation embeds |
| `ExactMatch`          | Deterministic exact string match                  |
| `create_llm_evaluator`| Custom prompt-based LLM-as-judge                  |

#### CLI reference

| Command                               | Description                                     |
| ------------------------------------- | ----------------------------------------------- |
| `pixie test [path]`                   | Run eval tests; open scorecard in browser       |
| `pixie trace --runnable R --input I --output O` | Run a Runnable, capture trace to JSONL |
| `pixie format --input I --output O`   | Convert a trace JSONL to a dataset entry JSON   |
| `pixie analyze <test_run_id>`         | LLM analysis of a completed test run            |
| `pixie init [root]`                   | Scaffold the `pixie_qa/` working directory      |
| `pixie start [root]`                  | Launch the web UI at `http://localhost:7118`     |

### 5. Web UI section

```bash
pixie start              # opens http://localhost:7118
pixie start my_dir       # custom artifact root
```

Tabbed navigation for results, scorecards, datasets, and markdown files.
Live-updating via SSE.

### 6. Configuration section

Pixie reads from environment variables and a `.env` file. Existing process env vars
take priority over `.env` values.

| Variable                    | Description                                     |
| --------------------------- | ----------------------------------------------- |
| `PIXIE_ROOT`                | Root directory for all generated artefacts      |
| `PIXIE_RATE_LIMIT_ENABLED`  | `true` to enable evaluator throttling           |
| `PIXIE_RATE_LIMIT_RPS`      | Requests per second                             |
| `PIXIE_RATE_LIMIT_RPM`      | Requests per minute                             |
| `PIXIE_RATE_LIMIT_TPS`      | Tokens per second                               |
| `PIXIE_RATE_LIMIT_TPM`      | Tokens per minute                               |

## Tone & style

- Developer-focused, concise.
- Use tables for structured reference info (evaluators, CLI, config).
- Short code examples inline — not full tutorials.
- No marketing copy; explain what each piece does, not why it's amazing.
- Skill section first, then package section (skill is the primary entry point for
  most users).
