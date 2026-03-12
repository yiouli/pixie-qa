# Project: Email Classifier

## Entry point
`python extractor.py` — runs 4 sample emails through `extract_from_email` and prints JSON.

## Instrumented spans
- `extract_from_email(email_text: str)` — `@observe(name="extract_from_email")` wraps the full pipeline
  - eval_input: `{"email_text": str}`
  - eval_output: `{"category": str, "priority": str, "summary": str}` (dict)

## Datasets
- `email-classifier-golden`: 6 items covering billing, technical, account, general categories and various priority levels

## Eval plan
- Evaluator 1: `ValidJSONEval` — verifies output is valid JSON (serialisable dict with required keys)
- Evaluator 2: Custom `json_structure_eval` — verifies `category`, `priority`, and `summary` keys exist and have valid enum values
- from_trace: `root` (the `@observe` span — no real LLM call)
- Pass criteria: `ScoreThreshold(threshold=1.0, pct=1.0)` for structure checks (deterministic rules, should always pass)
- Test file: `tests/test_email_classifier.py::test_json_structure`

## Known issues / findings
- App is fully deterministic (keyword rules, no LLM). Structure tests should always pass.
- `ValidJSONEval` works on the string representation of the output; output is already a dict so it will be serialised.
