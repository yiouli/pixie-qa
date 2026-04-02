# Step 1c: Eval Criteria

Define what quality dimensions matter for this app — based on the entry point (01-entry-point.md) and data flow (02-data-flow.md) you've already documented.

This document serves two purposes:

1. **Dataset creation (Step 4)**: The use cases tell you what kinds of eval_input items to generate — each use case should have representative items in the dataset.
2. **Test implementation (Step 5)**: The eval criteria tell you what evaluators to choose and what to assert on.

Keep this concise — it's a planning artifact, not a comprehensive spec.

---

## What to define

### 1. Use cases

List the distinct scenarios the app handles. Each use case becomes a category of eval_input items in your dataset. One line per use case is enough.

### 2. Eval criteria

Define **high-level, application-specific eval criteria** — quality dimensions that matter for THIS app. Each criterion will map to an evaluator in Step 5.

**Good criteria are specific to the app's purpose.** Examples:

- Voice customer support agent: "Does the agent verify the caller's identity before transferring?", "Are responses concise enough for phone conversation?"
- Research report generator: "Does the report address all sub-questions?", "Are claims supported by retrieved sources?"
- RAG chatbot: "Are answers grounded in the retrieved context?", "Does it say 'I don't know' when context is missing?"

**Bad criteria are generic evaluator names dressed up as requirements.** Don't say "Factual accuracy" or "Response relevance" — say what factual accuracy or relevance means for THIS app.

At this stage, don't pick evaluator classes or thresholds. That comes in Step 5.

### 3. Check criteria are observable

For each criterion, verify that the data flow in `02-data-flow.md` includes the data needed to evaluate it. If a criterion requires data that isn't in the processing stack, note what additional instrumentation is needed in Step 2.

---

## Output: `pixie_qa/03-eval-criteria.md`

Write your findings to this file. **Keep it short** — the template below is the maximum length.

### Template

```markdown
# Eval Criteria

## Use cases

1. <Use case name>: <one-line description>
2. ...

## Eval criteria

| #   | Criterion | Observable data needed |
| --- | --------- | ---------------------- |
| 1   | ...       | ...                    |
| 2   | ...       | ...                    |

## Observability check

| Criterion | Available in data flow? | Gap? |
| --------- | ----------------------- | ---- |
| ...       | Yes / No                | ...  |
```
