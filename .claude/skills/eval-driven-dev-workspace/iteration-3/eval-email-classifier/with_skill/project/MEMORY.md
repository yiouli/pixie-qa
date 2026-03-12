# Project: Email Classifier Eval

## Entry point
`python extractor.py` — runs 4 sample emails through `extract_from_email`

## Instrumented spans
- `extract_from_email(email_text: str)` — @observe wraps the full pipeline
  - eval_input: {"email_text": str}
  - eval_output: dict with keys: category, priority, summary

## Datasets
- `email-classifier-golden`: 7 items covering normal cases and edge cases

## Eval plan
- Evaluator: `ValidJSONEval` with a JSON schema checking required keys and valid enum values
- Custom evaluator: `json_structure_eval` for detailed structural checks
- Pass criteria: `ScoreThreshold(1.0, pct=1.0)` — all outputs must have valid structure
- Test file: `tests/test_classifier.py`

## Known issues / findings
- App is purely heuristic (no LLM), so no API key needed
- Output is a Python dict (not a JSON string), so ValidJSONEval evaluates the dict serialized as JSON
- The eval covers: category enum validity, priority enum validity, summary non-empty
