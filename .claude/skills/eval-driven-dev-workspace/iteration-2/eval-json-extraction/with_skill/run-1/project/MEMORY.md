# Project: email-extraction eval

## Entry point

```
python extractor.py          # ad-hoc smoke test (prints JSON dicts)
python build_dataset.py      # populate pixie_datasets/email-extraction.json
pixie-test tests/            # run all eval tests
pixie-test tests/ -v         # verbose output with per-case scores
```

## Application summary

`extractor.py` → `extract_from_email(email_text: str) -> dict`

Uses GPT-4o-mini with a zero-shot system prompt to classify customer support
emails into a structured JSON dict with three fields:
- `category`: one of `"billing" | "technical" | "account" | "general"`
- `priority`: one of `"low" | "medium" | "high"`
- `summary`: a one-sentence description of the issue

## Instrumented spans

`extract_from_email(email_text)` — decorated with `@px.observe(name="extract_from_email")`

- `eval_input`:  `{"email_text": str}` (the raw email)
- `eval_output`: `dict` with `category`, `priority`, `summary`

`enable_storage()` is called at module `__main__` startup and inside the
test runnable.

## Dataset

**Name:** `email-extraction`
**Location:** `pixie_datasets/email-extraction.json` (relative to project dir)
**Size:** 6 items
**Built via:** `build_dataset.py` (Python API — `DatasetStore` + `Evaluable`)

### Item summary

| # | Category  | Priority | Email snippet                                      |
|---|-----------|----------|----------------------------------------------------|
| 0 | billing   | high     | charged twice this month                           |
| 1 | technical | high     | app keeps crashing on uploads > 10 MB              |
| 2 | account   | low      | how to reset my password                           |
| 3 | general   | low      | educational discounts for university students      |
| 4 | technical | medium   | dark mode text invisible on iOS                    |
| 5 | billing   | medium   | cancelled subscription still shows as active       |

## Eval plan

| Test | Evaluator | Criteria | What it checks |
|---|---|---|---|
| `test_valid_json_schema` | `ValidJSONEval(schema=...)` | 100% score ≥ 1.0 | Output is valid JSON matching the JSON Schema (enum values, required keys) |
| `test_required_keys_present` | `required_keys_eval` (custom) | 100% score ≥ 1.0 | category, priority, summary all present and non-empty |
| `test_json_structure_diff` | `JSONDiffEval()` | 80% score ≥ 0.6 | Structural similarity to expected_output |
| `test_category_classification` | `category_exact_eval` (custom) | 100% score ≥ 1.0 | category exactly matches expected label |
| `test_priority_classification` | `priority_exact_eval` (custom) | 80% score ≥ 1.0 | priority exactly matches expected label |

All evaluators are heuristic — no LLM judge / API key required for eval.

## Files created

```
extractor.py          ← instrumented (added @px.observe + enable_storage)
build_dataset.py      ← builds pixie_datasets/email-extraction.json
tests/
  __init__.py
  test_email_extraction.py  ← 5 async test functions
MEMORY.md             ← this file
```

## Known issues / findings

- `extract_from_email` makes a real OpenAI call. Running tests requires
  `OPENAI_API_KEY` to be set in the environment.
- `build_dataset.py` does NOT call the model — dataset items are hand-labelled
  synthetic examples, so it can be run without an API key.
- `test_json_structure_diff` uses a relaxed threshold (0.6 / 80%) because
  the `summary` field is free-text and will never exactly match the expected
  string; JSONDiffEval will score it lower than the enum fields.
- If `test_priority_classification` flakiness is observed, tighten/loosen
  `pct` in the `ScoreThreshold`.
