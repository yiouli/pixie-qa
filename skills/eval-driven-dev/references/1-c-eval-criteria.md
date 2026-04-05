# Step 1c: Eval Criteria

Define what quality dimensions matter for this app — based on the entry point (01-entry-point.md) and data flow (02-data-flow.md) you've already documented.

This document serves two purposes:

1. **Dataset creation (Step 5)**: The use cases tell you what kinds of eval_input items to generate — each use case should have representative items in the dataset.
2. **Evaluator selection (Step 4)**: The eval criteria tell you what evaluators to choose and how to map them.

Keep this concise — it's a planning artifact, not a comprehensive spec.

---

## What to define

### 1. Use cases

List the distinct scenarios the app handles. Each use case becomes a category of eval_input items in your dataset. **Each use case description must be a concise one-liner that conveys both (a) what the input is and (b) what the expected behavior or outcome is.** The description should be specific enough that someone unfamiliar with the app can understand the scenario and its success criteria.

**Good use case descriptions:**

- "Reroute to human agent on account lookup difficulties"
- "Answer billing question using customer's plan details from CRM"
- "Decline to answer questions outside the support domain"
- "Summarize research findings including all queried sub-topics"

**Bad use case descriptions (too vague):**

- "Handle billing questions"
- "Edge case"
- "Error handling"

### 2. Eval criteria

Define **high-level, application-specific eval criteria** — quality dimensions that matter for THIS app. Each criterion will map to an evaluator in Step 4.

**Good criteria are specific to the app's purpose.** Examples:

- Voice customer support agent: "Does the agent verify the caller's identity before transferring?", "Are responses concise enough for phone conversation?"
- Research report generator: "Does the report address all sub-questions?", "Are claims supported by retrieved sources?"
- RAG chatbot: "Are answers grounded in the retrieved context?", "Does it say 'I don't know' when context is missing?"

**Bad criteria are generic evaluator names dressed up as requirements.** Don't say "Factual accuracy" or "Response relevance" — say what factual accuracy or relevance means for THIS app.

At this stage, don't pick evaluator classes or thresholds. That comes in Step 4.

### 3. Check criteria applicability and observability

For each criterion:

1. **Determine applicability scope** — does this criterion apply to ALL use cases, or only a subset? If a criterion is only relevant for certain scenarios (e.g., "identity verification" only applies to account-related requests, not general FAQ), mark it clearly. This distinction is critical for Step 5 (dataset creation) because:
   - **Universal criteria** → become dataset-level default evaluators
   - **Case-specific criteria** → become item-level evaluators on relevant rows only

2. **Verify observability** — check that the data flow in `02-data-flow.md` includes the data needed to evaluate each criterion. If a criterion requires data that isn't in the processing stack, note what additional instrumentation is needed in Step 2.

---

## Output: `pixie_qa/03-eval-criteria.md`

Write your findings to this file. **Keep it short** — the template below is the maximum length.

### Template

```markdown
# Eval Criteria

## Use cases

1. <Use case name>: <one-liner conveying input + expected behavior>
2. ...

## Eval criteria

| #   | Criterion | Applies to    | Observable data needed |
| --- | --------- | ------------- | ---------------------- |
| 1   | ...       | All           | ...                    |
| 2   | ...       | Use case 1, 3 | ...                    |

## Observability check

| Criterion | Available in data flow? | Gap? |
| --------- | ----------------------- | ---- |
| ...       | Yes / No                | ...  |
```
