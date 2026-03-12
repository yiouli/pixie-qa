# pixie-qa

A Claude skill and Python package for **eval-driven development** of LLM-powered applications.

Use this skill to instrument your app, build golden datasets from real runs, write eval-based tests, and catch regressions before they ship — all from a single conversation with Claude.

## What the Skill Does

The `eval-driven-dev` skill guides Claude through the full QA loop for LLM applications:

1. **Understand the app** — read the codebase, trace the data flow, learn what the app is supposed to do
2. **Instrument it** — add `enable_storage()` and `@observe` so every run is captured to a local SQLite database
3. **Build a dataset** — save representative traces as test cases with `pixie dataset save`
4. **Write eval tests** — generate `test_*.py` files with `assert_dataset_pass` and appropriate evaluators
5. **Run the tests** — `pixie-test` to run all evals and report per-case scores
6. **Investigate failures** — look up the stored trace for each failure, diagnose, fix, repeat

## Getting Started

### 1. Add the skill to Claude

The skill is bundled in this repository. Claude will automatically use it when you ask to evaluate, test, QA, or benchmark an LLM-powered Python project.

If you are using an openskills-compatible agent host:

```bash
npx openskills install anthropics/skills
```

### 2. Install the `pixie-qa` package in your project

```bash
pip install pixie-qa          # or: uv add pixie-qa
```

Provider instrumentation extras:

```bash
pip install "pixie-qa[openai]"       # OpenAI
pip install "pixie-qa[anthropic]"    # Anthropic
pip install "pixie-qa[langchain]"    # LangChain
pip install "pixie-qa[all]"          # all providers
```

### 3. Ask Claude to set up evals

Open a conversation and describe your project:

> "I have a RAG chatbot in `app/chatbot.py`. Help me set up evals to make sure it's giving accurate answers."

Claude will read your code, instrument it, build a dataset from a few real runs, write tests, and run them for you.

## Skill Workflow Example

Here is a quick summary of what Claude does end-to-end:

```python
# Claude instruments your app entry point
from pixie import enable_storage, observe

enable_storage()              # one line: creates DB, registers handler

# Claude adds @observe on the function to test
@observe(name="answer_question")
def answer_question(question: str) -> str:
    ...
```

```bash
# After running the app with a few real inputs:
pixie dataset create qa-golden-set
pixie dataset save qa-golden-set
```

```python
# Claude writes tests/test_qa.py with:
from pixie import assert_dataset_pass, FactualityEval, ScoreThreshold

async def test_factuality():
    await assert_dataset_pass(
        runnable=runnable,
        dataset_name="qa-golden-set",
        evaluators=[FactualityEval()],
        pass_criteria=ScoreThreshold(threshold=0.7, pct=0.8),
    )
```

```bash
# Then runs:
pixie-test -v
```

All symbols are importable from the top-level `pixie` package — no need for submodule paths.

## Repository Structure

```
pixie/          Python package (instrumentation, storage, evals, dataset, cli)
specs/          Design specs and architecture docs
changelogs/     Per-feature change history
.claude/skills/ Claude skill definitions and benchmarks
```

## Python Package

The `pixie-qa` Python package (imported as `pixie`) is what Claude installs and uses inside your project. For the package API and CLI reference, see [docs/package.md](docs/package.md).
