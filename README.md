# Pixie-QA

[![Skill](https://img.shields.io/badge/Skill-eval--driven--dev-blueviolet?style=flat&logo=anthropic&logoColor=white)](https://skills.sh/github/awesome-copilot/eval-driven-dev)
[![PyPI package](https://img.shields.io/pypi/v/pixie-qa?logo=pypi&logoColor=white&style=flat)](https://badge.fury.io/py/pixie-qa)
[![Discord](https://img.shields.io/discord/1459772566528069715?logo=discord&logoColor=white&label=Discord&color=34b76a&style=flat)](https://discord.gg/7fmXQzFt)

## Agent skill for Evaluation Driven Development

Pixie-QA is an agent skill that let your coding agent to systematically improve the quality of your AI application with Evaluation Driven Development (EDD) approach. With the skill, your coding agent will carry out the evaluate->analyze->implement cycle for you.

## Why Pixie-QA?

You've probably spent a lot of time tweaking your implementation for your AI feature, re-testing the same inputs, and not being sure whether things actually got better.

You might have looked at evals products, but think they are not worth the hassle - they are good at giving you fancy metrics and dashboards, but provides little help on actually improving your application.

Pixie-QA takes a different approach, focusing on producing actionable insights — specific action items that you or your coding agent can investigate further or directly implement in your code.

And because Pixie-QA runs locally inside your codebase, your data stays private and you're not locked into another platform.

## Demo

[Demo Video](https://github.com/user-attachments/assets/74565bd2-a7fc-4f31-909d-9697642e033d)

## How it Works

The skill guides your coding agent (Claude Code, Cursor, GitHub Copilot, etc.) through a 6-step pipeline:

1. **Analyze the app** — The agent reads your codebase, identifies entry points, maps capabilities, and defines eval criteria based on real failure modes (not generic quality checklists).

2. **Instrument data boundaries** — Lightweight `wrap()` calls are added where your app reads external data (databases, APIs, caches) and where it produces output. This lets the eval harness inject controlled inputs and capture results — without changing your app's logic.

3. **Build a Runnable** — A thin adapter that lets the eval harness invoke your app the same way a real user would. Your app runs its real code path, makes real LLM calls — nothing is mocked.

4. **Define evaluators** — Each eval criterion maps to a scoring function: LLM-as-judge for semantic quality, deterministic checks for structural requirements, or custom evaluators for domain-specific rules.

5. **Build a dataset** — Test cases with realistic inputs, pre-captured external data, and expected behavior. Each entry specifies which evaluators to run and what passing looks like.

6. **Run `pixie test` and analyze** — The harness runs all entries concurrently, scores them, and the agent analyzes results: which entries failed, why, and what to fix — in the app or in the eval setup itself.

The output is a working eval pipelinem and detailed analysis + action plan that you or your coding agent can implement.

## Get Started

Add the skill to your coding agent:

```bash
npx skills add yiouli/pixie-qa
```

Then simply talk to your coding agent in your project, e.g:

- "Setup eval"
- "Improve my agent's output quality"
- "The AI response is wrong when ..., please fix"
