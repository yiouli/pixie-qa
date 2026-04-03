# pixie-qa

An agent skill that make coding agent the QA engineer for LLM applications.

## What the Skill Does

The `qa-eval` skill guides your coding agent through the full eval-based QA loop for LLM applications:

1. **Understand the code** — read the codebase, trace the data flow, learn what the code is supposed to do
2. **Instrument it** — add `enable_storage()` and `@observe` so every run is captured to a local SQLite database
3. **Build a dataset** — save representative traces as test cases with `pixie dataset save`
4. **Write eval tests** — generate `test_*.py` files with `assert_dataset_pass` and appropriate evaluators
5. **Run the tests** — `pixie test` to run all evals and report per-case scores
6. **Analyse results** — `pixie analyze <test_id>` to get LLM-generated analysis of test results
7. **Investigate failures** — look up the stored trace for each failure, diagnose, fix, repeat

## Getting Started

### 1. Add the skill to your coding agent

```bash
npx skills add yiouli/pixie-qa
```

The accompanying python package would be installed by the skill automatically when it's used.

### 2. Ask coding agent to set up evals

Open a conversation and say something like when developing a python based AI project:

> "setup QA for my agent"

Your coding agent will read your code, instrument it, build a dataset from a few real runs, write and run eval-based tests, investigate failures and fix.

## Python Package

The `pixie-qa` Python package (imported as `pixie`) is what Claude installs and uses inside your project. For the package API and CLI reference, see [docs/package.md](docs/package.md).

## Web UI

View all eval artifacts (results, markdown docs, datasets, and legacy scorecards) in a live-updating local web UI:

```bash
pixie start              # initializes pixie_qa/ (if needed) and opens http://localhost:7118
pixie start my_dir       # use a custom artifact root
pixie init               # scaffolds pixie_qa/ without starting the server
```

The web UI provides tabbed navigation for results, scorecards (legacy), datasets, and markdown files. Changes to artifacts are pushed to the browser in real time via SSE.

The server writes a `server.lock` file to the artifact root directory on startup (containing the port number) and removes it on shutdown, allowing other processes to discover whether the server is already running.

## Configuration

Pixie reads configuration from environment variables and a local `.env` file through a single central config layer. Existing process env vars win over `.env` values.

Useful settings include:

- `PIXIE_ROOT` to move all generated artefacts under a different root directory
- `PIXIE_RATE_LIMIT_ENABLED=true` to enable evaluator throttling for `pixie test`
- `PIXIE_RATE_LIMIT_RPS`, `PIXIE_RATE_LIMIT_RPM`, `PIXIE_RATE_LIMIT_TPS`, and `PIXIE_RATE_LIMIT_TPM` to tune request and token throughput for LLM-as-judge evaluators
