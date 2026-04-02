---
name: eval-driven-dev
description: >
  Set up eval-based QA for Python LLM applications: instrument the app, build golden datasets,
  write and run eval tests, and iterate on failures.
  ALWAYS USE THIS SKILL when the user asks to set up QA, add tests, add evals,
  evaluate, benchmark, fix wrong behaviors, improve quality, or do quality assurance for any Python project that calls an LLM model.
license: MIT
compatibility: Python 3.11+
metadata:
  version: 0.3.0
  pixie-qa-version: ">=0.3.0,<0.4.0"
  pixie-qa-source: https://github.com/yiouli/pixie-qa/
---

# Eval-Driven Development for Python LLM Applications

You're building an **automated QA pipeline** that tests a Python application end-to-end — running it the same way a real user would, with real inputs — then scoring the outputs using evaluators and producing pass/fail results via `pixie test`.

**What you're testing is the app itself** — its request handling, context assembly (how it gathers data, builds prompts, manages conversation state), routing, and response formatting. The app uses an LLM, which makes outputs non-deterministic — that's why you use evaluators (LLM-as-judge, similarity scores) instead of `assertEqual` — but the thing under test is the app's code, not the LLM.

**What's in scope**: the app's entire code path from entry point to response — never mock or skip any part of it. **What's out of scope**: external data sources the app reads from (databases, caches, third-party APIs, voice streams) — mock these to control inputs and reduce flakiness.

**The deliverable is a working `pixie test` run with real scores** — not a plan, not just instrumentation, not just a dataset.

This skill is about doing the work, not describing it. Read code, edit files, run commands, produce a working pipeline.

---

## Before you start

Run the setup script to update the skill, install `pixie-qa` with all optional provider packages, and initialize the pixie working directory. If any step fails or is blocked by the environment, continue — do not let failures here block the rest of the workflow.

```bash
bash resources/setup.sh
```

---

## The workflow

Follow Steps 1–5 straight through without stopping. Do not ask the user for confirmation at intermediate steps — verify each step yourself and continue.

**How to work — read this before doing anything else:**

- **One step at a time.** Read only the current step's instructions. Do NOT read Steps 2–5 while working on Step 1.
- **Read references only when a step tells you to.** Each step names a specific reference file. Read it when you reach that step — not before.
- **Create artifacts immediately.** After reading code for a sub-step, write the output file for that sub-step before moving on. Don't accumulate understanding across multiple sub-steps before writing anything.
- **Verify, then move on.** Each step has a checkpoint. Verify it, then proceed to the next step. Don't plan future steps while verifying the current one.

**Run Steps 1–6 in sequence.** If the user's prompt makes it clear that earlier steps are already done (e.g., "run the existing tests", "re-run evals"), skip to the appropriate step. When in doubt, start from Step 1.

---

### Step 1: Understand the app and define eval criteria

**First, check the user's prompt for specific requirements.** Before reading app code, examine what the user asked for:

- **Referenced documents or specs**: Does the prompt mention a file to follow (e.g., "follow the spec in EVAL_SPEC.md", "use the methodology in REQUIREMENTS.md")? If so, **read that file first** — it may specify datasets, evaluation dimensions, pass criteria, or methodology that override your defaults.
- **Specified datasets or data sources**: Does the prompt reference specific data files (e.g., "use questions from eval_inputs/research_questions.json", "use the scenarios in call_scenarios.json")? If so, **read those files** — you must use them as the basis for your eval dataset, not fabricate generic alternatives.
- **Specified evaluation dimensions**: Does the prompt name specific quality aspects to evaluate (e.g., "evaluate on factuality, completeness, and bias", "test identity verification and tool call correctness")? If so, **every named dimension must have a corresponding evaluator** in your test file.

If the prompt specifies any of the above, they take priority. Read and incorporate them before proceeding.

Step 1 has three sub-steps. Each reads its own reference file and produces its own output file. **Complete each sub-step fully before starting the next.**

#### Sub-step 1a: Entry point & execution flow

> **Reference**: Read `references/1-a-entry-point.md` now.

Read the source code to understand how the app starts and how a real user invokes it. Write your findings to `pixie_qa/01-entry-point.md` before moving on.

> **Checkpoint**: `pixie_qa/01-entry-point.md` written with entry point, execution flow, user-facing interface, and env requirements.

#### Sub-step 1b: Processing stack & data flow (DAG artifact)

> **Reference**: Read `references/1-b-data-flow.md` now.

Starting from the entry point you documented, trace the full processing stack and produce a **structured DAG JSON file** at `pixie_qa/02-data-flow.json`. The DAG has the common ancestor of LLM calls as root and contains every data dependency, intermediate state, LLM call, and side-effect as nodes with metadata and parent pointers.

After writing the JSON, validate it:

```bash
uv run pixie dag validate pixie_qa/02-data-flow.json
```

This checks the DAG structure, verifies code pointers exist, and generates a Mermaid diagram at `pixie_qa/02-data-flow.md`. If validation fails, fix the errors and re-run.

> **Checkpoint**: `pixie_qa/02-data-flow.json` written and `pixie dag validate` passes. Mermaid diagram generated at `pixie_qa/02-data-flow.md`.
>
> **Schema reminder**: DAG node `name` must be unique, meaningful, and lower_snake_case (for example, `handle_turn`). If a node represents an LLM provider call, set `is_llm_call: true` (otherwise omit it or set `false`). Name-matching rules for `@observe` / `start_observation(...)` are defined in instrumentation guidance (Step 2), not here.

#### Sub-step 1c: Eval criteria

> **Reference**: Read `references/1-c-eval-criteria.md` now.

Define the app's use cases and eval criteria. Use cases drive dataset creation (Step 4); eval criteria drive evaluator selection (Step 5). Verify each criterion is observable based on the data flow. Write your findings to `pixie_qa/03-eval-criteria.md` before moving on.

> **Checkpoint**: `pixie_qa/03-eval-criteria.md` written with use cases, eval criteria, and observability check. Do NOT read Step 2 instructions yet.

---

### Step 2: Instrument and observe a real run

> **Reference**: Read `references/2-instrument-and-observe.md` now — it has the detailed sub-steps for DAG-based instrumentation, running the app, verifying the trace against the DAG, documenting the reference trace, and the `@observe` and `enable_storage()` rules and patterns.

Add `@observe` to application-level functions identified in your DAG (`pixie_qa/02-data-flow.json`). Run the app normally (no mocks) to produce a reference trace. Verify the trace with `pixie trace verify`, then validate it matches the DAG with `pixie dag check-trace`. Document the data shapes.

> **Checkpoint**: `pixie_qa/04-reference-trace.md` exists with eval_input/eval_output shapes and completeness verification. Instrumentation is in the source code. `pixie dag check-trace` passes. Do NOT read Step 3 instructions yet.

---

### Step 3: Write a utility function to run the full app end-to-end

> **Reference**: Read `references/3-run-harness.md` now — it has the contract, implementation guidance, verification steps, and concrete examples by app type (FastAPI, CLI, standalone function).

Write a `run_app(eval_input) → eval_output` function that patches external dependencies, calls the app through its real entry point, and collects the response. Verify it produces the same structure as the reference trace.

> **Checkpoint**: Utility function implemented and verified. When fed the reference trace's eval_input, it produces eval_output with the same structure and exercises the same code path. Do NOT read Step 4 instructions yet.

---

### Step 4: Build the dataset

> **Reference**: Read `references/4-build-dataset.md` now — it has the sub-steps for determining expectations, generating eval_input items, validating the dataset, the dataset creation API, and the validation checklist.

Create a dataset of made-up eval_input items that match the data shape from the reference trace. Add case-specific `expected_output` where needed. Run the build script and validate diversity and structural correctness.

> **Checkpoint**: Dataset created with diverse eval_inputs matching the reference trace's data shape. Do NOT read Step 5 instructions yet.

---

### Step 5: Write and run eval tests

> **Reference**: Read `references/5-write-and-run-tests.md` now — it has the sub-steps for mapping criteria to evaluators, writing the test file, verifying the scorecard, the evaluator catalog, and test file boilerplate. **Re-read the API reference immediately before writing test code.**

Map each eval criterion to an evaluator, write a test file that wires the utility function + dataset + evaluators together, and run with `pixie test`.

> **Checkpoint**: Tests run and produce real scores.
>
> If the test errors out (import failures, missing keys), that's a setup bug — fix and re-run. But if tests produce real pass/fail scores, that's the deliverable.
>
> **STOP GATE — read this before doing anything else after tests produce scores:**
>
> - If the user's original prompt asks only for setup ("set up QA", "add tests", "add evals", "set up evaluations"), **STOP HERE**. Report the test results to the user: "QA setup is complete. Tests show N/M passing. [brief summary]. Want me to investigate the failures and iterate?" Do NOT proceed to Step 6.
> - If the user's original prompt explicitly asks for iteration ("fix", "improve", "debug", "iterate", "investigate failures", "make tests pass"), proceed to Step 6.

---

### Step 6: Investigate and iterate

> **Reference**: Read `references/6-investigation.md` now — it has the stop/continue decision, root-cause patterns, and investigation procedures. **Follow its instructions before doing any investigation work.**

---

## Web Server Management

pixie-qa runs a web server in the background for displaying context, traces, and eval results to the user. It's automatically started by the setup script, and need to be explicitly cleaned up when display is no longer needed.

When the user is done with the eval-driven-dev workflow, inform them the web server is still running and you can clean it up with the following command:

```bash
bash resources/stop-server.sh
```

And whenever you restart the workflow, always run the setup script again to ensure the web server is running:

```bash
bash resources/setup.sh
```
