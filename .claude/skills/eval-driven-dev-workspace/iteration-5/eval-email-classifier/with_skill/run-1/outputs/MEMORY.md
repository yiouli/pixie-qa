## Project: Email Classifier

### Entry point
`python extractor.py` or `extract_from_email(email_text)` directly.

### How to run
```bash
cd /home/yiouli/repo/pixie-qa/.claude/skills/eval-driven-dev-workspace/iteration-5/eval-email-classifier/with_skill/project
PYTHONPATH=/home/yiouli/repo/pixie-qa python extractor.py
```

### Instrumented spans
- `extract_from_email(email_text: str)` — `@observe` wraps the full classifier pipeline
  - `eval_input`: `{"email_text": str}`
  - `eval_output`: `{"category": str, "priority": str, "summary": str}`

### Use cases handled
- **billing**: keywords like charge, refund, invoice, payment, billing, subscription
- **technical**: keywords like crash, error, bug, broken, not working, upload, download
- **account**: keywords like password, login, account, username, sign in, reset
- **general**: anything else (fallback)

Priority tiers:
- **high**: urgent, asap, immediately, critical, crashing, duplicate charge
- **medium**: soon, when possible, annoying, frustrating
- **low**: default

Summary: first sentence, truncated to 100 chars.

### Datasets
- `email-classifier-golden`: 6 items covering all 4 categories, multiple priority levels, and edge cases
  - billing/high: duplicate charge ASAP
  - technical/high: app crashing urgently
  - account/low: reset password query
  - general/low: dark mode feature request
  - billing/low: subscription question (no urgency keywords)
  - technical/medium: frustrating bug report

### Eval plan
- Evaluator: `JSONDiffEval` (heuristic, no LLM needed) comparing `category` and `priority` fields
- Pass criteria: `ScoreThreshold(threshold=0.8, pct=0.8)` — 80% of cases must score ≥ 0.8
- `from_trace`: `root` (the `extract_from_email` span is the root)
- Test file: `tests/test_email_classifier.py::test_classification`

### Known issues / findings
- The mock classifier uses simple keyword rules — no LLM calls, so `last_llm_call` won't be available
- `JSONDiffEval` compares the full dict; expected_output should match the exact structure returned
- Summary field is derived deterministically from the first sentence, so it can be included in expected output
