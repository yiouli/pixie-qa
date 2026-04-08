---
name: eval-driven-dev
description: >
  Set up eval-based QA for Python LLM applications: instrument the app with wrap(),
  build golden datasets, write and run eval tests, and iterate on failures.
  ALWAYS USE THIS SKILL when the user asks to set up QA, add tests, add evals,
  evaluate, benchmark, fix wrong behaviors, improve quality, or do quality assurance for any Python project that calls an LLM model.
license: MIT
compatibility: Python 3.11+
metadata:
  version: 0.6.0
  pixie-qa-version: ">=0.6.0,<0.7.0"
  pixie-qa-source: https://github.com/yiouli/pixie-qa/
---

# Eval-Driven Development for Python LLM Applications

You're building an **automated QA pipeline** that tests a Python application end-to-end — running it the same way a real user would, with real inputs — then scoring the outputs using evaluators and producing pass/fail results via `pixie test`.

**What you're testing is the app itself** — its request handling, context assembly (how it gathers data, builds prompts, manages conversation state), routing, and response formatting. The app uses an LLM, which makes outputs non-deterministic — that's why you use evaluators (LLM-as-judge, similarity scores) instead of `assertEqual` — but the thing under test is the app's code, not the LLM.

**What's in scope**: the app's entire code path from entry point to response — never mock or skip any part of it. **What's out of scope**: external data sources the app reads from (databases, caches, third-party APIs, voice streams) — these are handled automatically by `wrap(purpose="input")` at test time.

**The deliverable is a working `pixie test` run with real scores** — not a plan, not just instrumentation, not just a dataset.

This skill is about doing the work, not describing it. Read code, edit files, run commands, produce a working pipeline.

---

## Before you start

**First, activate the virtual environment**. Identify the correct virtual environment for the project and activate it. After the virtual environment is active, run setup:

```bash
bash resources/setup.sh
```

The script updates the `eval-driven-dev` skill and `pixie-qa` python package to latest version, and initialize the pixie working directory if it's not already initialized. If the skill or package update fails, continue — do not let these failures block the rest of the workflow.

---

## The workflow

Follow Steps 1–6 straight through without stopping. Do not ask the user for confirmation at intermediate steps — verify each step yourself and continue.

**How to work — read this before doing anything else:**

- **One step at a time.** Read only the current step's instructions. Do NOT read Steps 2–6 while working on Step 1.
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

Step 1 has two sub-steps. Each reads its own reference file and produces its own output file. **Complete each sub-step fully before starting the next.**

#### Sub-step 1a: Entry point & execution flow

> **Reference**: Read `references/1-a-entry-point.md` now.

Read the source code to understand how the app starts and how a real user invokes it. Write your findings to `pixie_qa/01-entry-point.md` before moving on.

> **Checkpoint**: `pixie_qa/01-entry-point.md` written with entry point, execution flow, user-facing interface, and env requirements.

#### Sub-step 1b: Eval criteria

> **Reference**: Read `references/1-b-eval-criteria.md` now.

Define the app's use cases and eval criteria. Use cases drive dataset creation (Step 4); eval criteria drive evaluator selection (Step 3). For each criterion, determine whether it applies to all scenarios or only a subset — this drives whether it becomes a dataset-level default evaluator or an item-level evaluator. Write your findings to `pixie_qa/02-eval-criteria.md` before moving on.

> **Checkpoint**: `pixie_qa/02-eval-criteria.md` written with use cases (each with a one-liner conveying input + expected behavior), eval criteria with applicability scope, and a note on what data needs to be captured to evaluate each criterion. Do NOT read Step 2 instructions yet.

---

### Step 2: Instrument with `wrap` and capture a reference trace

> **Reference**: Read `references/2-wrap-and-trace.md` now — it has the sub-steps for data-flow analysis, adding `wrap()` calls, implementing the Runnable class, running `pixie trace` to capture a reference trace, and verifying coverage.

Add `wrap()` calls at data boundaries in the application code. Implement a `Runnable` class with `setup`, `run`, and `teardown` methods. **Note**: `run()` is called concurrently for all dataset entries — if the app uses shared mutable state (SQLite, global caches), add concurrency protection (see the reference doc for patterns). Imports from project modules work automatically — no `sys.path` manipulation needed.

Run `pixie trace` to capture a reference trace. Verify all eval criteria have corresponding wrap coverage.

> **Checkpoint**: `pixie_qa/scripts/run_app.py` written and verified. `pixie_qa/reference-trace.jsonl` exists and all expected data points appear when formatted with `pixie format`. Do NOT read Step 3 instructions yet.

---

### Step 3: Define evaluators

> **Reference**: Read `references/3-define-evaluators.md` now — it has the sub-steps for mapping criteria to evaluators, implementing custom evaluators, verifying discoverability, and producing the evaluator mapping artifact.

Map each eval criterion from Step 1b to a concrete evaluator — implement custom ones where needed. Then produce the evaluator mapping artifact.

> **Checkpoint**: All evaluators implemented. `pixie_qa/03-evaluator-mapping.md` written with criterion-to-evaluator mapping using exact evaluator names (built-in names from `evaluators.md`, custom names in `filepath:callable_name` format). Do NOT read Step 4 instructions yet.

---

### Step 4: Build the dataset

> **Reference**: Read `references/4-build-dataset.md` now — it has the sub-steps for using `pixie format` for data shapes, generating dataset entries with `entry_kwargs` and `eval_input`, building the dataset JSON, and understanding the `expectation` vs `eval_output` distinction.

Use `pixie format` on the reference trace to get exact data shapes. Create a dataset JSON with entries containing:

- **`entry_kwargs`** — runnable arguments
- **`eval_input`** — list of `{"name": ..., "value": ...}` objects for wrap inputs
- **`description`** — human-readable label for the test case
- **`expectation`** — optional reference for comparison-based evaluators
- **`evaluators`** — optional per-entry evaluator list

All fields are top-level on each entry (no nesting). Set the `runnable` to the `filepath:ClassName` reference from Step 2. Assign evaluators from Step 3 — dataset-level defaults in the top-level `evaluators` array, per-entry overrides in each entry's `evaluators` field.

> **Checkpoint**: Dataset JSON created at `pixie_qa/datasets/<name>.json` with diverse entries, `entry_kwargs`, `eval_input`, `runnable`, evaluators, and descriptions. Do NOT read Step 5 instructions yet.

---

### Step 5: Run evaluation-based tests

> **Reference**: Read `references/5-run-tests.md` now — it has the sub-steps for running tests, fixing dataset quality issues, and running analysis.

Run `pixie test` to execute the full evaluation pipeline. Fix any data validation errors (`WrapRegistryMissError`, `WrapTypeMismatchError`, import failures). Once tests run cleanly, run `pixie analyze`.

> **Checkpoint**: Tests run and produce real scores. Analysis generated.
>
> If the test errors out (import failures, missing keys, runnable resolution errors), that's a setup bug — fix and re-run. But if tests produce real pass/fail scores, that's the deliverable.
>
> **STOP GATE — read this before doing anything else after tests produce scores:**
>
> - If the user's original prompt asks only for setup ("set up QA", "add tests", "add evals", "set up evaluations"), **STOP HERE**. Report the test results to the user: "QA setup is complete. Tests show N/M passing. [brief summary]. Want me to investigate the failures and iterate?" Do NOT proceed to Step 6.
> - If the user's original prompt explicitly asks for iteration ("fix", "improve", "debug", "iterate", "investigate failures", "make tests pass"), proceed to Step 6.

---

### Step 6: Investigate and iterate

> **Reference**: Read `references/6-investigate.md` now — it has the stop/continue decision, analysis review, root-cause patterns, and investigation procedures. **Follow its instructions before doing any investigation work.**

---

## Web Server Management

pixie-qa runs a web server in the background for displaying context, traces, and eval results to the user. It's automatically started by the setup script, and needs to be explicitly cleaned up when display is no longer needed.

When the user is done with the eval-driven-dev workflow, inform them the web server is still running and you can clean it up with the following command:

```bash
bash resources/stop-server.sh
```

And whenever you restart the workflow, always run the setup script again to ensure the web server is running:

```bash
bash resources/setup.sh
```
