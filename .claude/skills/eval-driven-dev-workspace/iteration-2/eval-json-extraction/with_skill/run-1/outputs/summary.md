# Eval-Driven Dev Run Summary

## Task
Add eval-based testing to `extractor.py` (email classifier) using pixie.

## What was done

### 1. Understood the application
- `extract_from_email(email_text: str) -> dict` calls GPT-4o-mini with a
  zero-shot system prompt and returns `{category, priority, summary}`.
- Entry point: `extractor.py` — three sample emails run via `__main__`.

### 2. Decided evaluation strategy
Because the output is a structured JSON dict with enum-constrained fields:
- Use `ValidJSONEval` with a JSON Schema to assert output format correctness.
- Use custom `required_keys_eval` to assert all three fields are present.
- Use `JSONDiffEval` for structural similarity against expected outputs.
- Use custom `category_exact_eval` / `priority_exact_eval` for label accuracy.
All evaluators are heuristic (no LLM judge required).

### 3. Instrumented the application
**File edited:** `extractor.py`
- Added `@px.observe(name="extract_from_email")` decorator to `extract_from_email`.
- Added `enable_storage()` call in `__main__` block.
- Added `px.flush()` after the sample loop.
- `eval_input` = `{"email_text": str}`, `eval_output` = the returned dict.

### 4. Built the dataset programmatically
**File created:** `build_dataset.py`
- Uses `DatasetStore` + `Evaluable` Python API — no model calls needed.
- Creates `pixie_datasets/email-extraction.json` with 6 hand-labelled items.
- Covers all four category types and all three priority levels.
- Each item has `eval_input` (email text) and `expected_output` (target dict).

### 5. Wrote eval tests
**File created:** `tests/test_email_extraction.py`

5 async test functions, all using `assert_dataset_pass`:

| Test | Evaluator | Pass criteria |
|---|---|---|
| `test_valid_json_schema` | `ValidJSONEval` with JSON Schema | 100% score = 1.0 |
| `test_required_keys_present` | custom `required_keys_eval` | 100% score = 1.0 |
| `test_json_structure_diff` | `JSONDiffEval` | 80% score ≥ 0.6 |
| `test_category_classification` | custom `category_exact_eval` | 100% score = 1.0 |
| `test_priority_classification` | custom `priority_exact_eval` | 80% score = 1.0 |

Run with: `pixie-test tests/` or `pixie-test tests/ -v`

### 6. Created memory file
**File created:** `MEMORY.md` — documents instrumented spans, dataset schema, eval plan, and known issues.

## Key decisions

- **Dataset built synthetically** (not from live runs) so it can be created
  without an API key and gives deterministic expected outputs.
- **Relaxed threshold for `test_json_structure_diff`** (0.6/80%) because the
  `summary` field is free-text and won't exactly match even a correct answer;
  JSONDiffEval will score it lower than the enum fields.
- **No LLM-as-judge evaluators** used — all checks are heuristic, keeping
  the eval suite runnable at zero additional LLM cost.

## Files modified / created

| Path (relative to PROJECT_DIR) | Change |
|---|---|
| `extractor.py` | Added `@px.observe`, `enable_storage()`, `px.flush()` |
| `build_dataset.py` | New — builds dataset via Python API |
| `tests/__init__.py` | New — package marker |
| `tests/test_email_extraction.py` | New — 5 eval tests |
| `MEMORY.md` | New — project notes |

## Prerequisites to run tests

```bash
export OPENAI_API_KEY=<your key>
cd <PROJECT_DIR>
python build_dataset.py   # creates pixie_datasets/email-extraction.json
pixie-test tests/ -v
```
