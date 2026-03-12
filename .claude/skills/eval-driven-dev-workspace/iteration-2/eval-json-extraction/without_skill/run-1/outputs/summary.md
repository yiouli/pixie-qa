# Email Classifier Eval Setup — Summary

## What was done

### 1. Instrumented extractor.py

`extract_from_email` was decorated with `@px.observe(name="extract_from_email")` from `pixie.instrumentation`. `px.init()` is called at module import time so the OTel pipeline is initialised automatically. A `px.flush()` call was added to the `__main__` block.

This means every call to `extract_from_email` is now captured as an `ObserveSpan` with the raw email text as `input` and the parsed JSON dict as `output`, making the trace available for eval harness consumption.

### 2. Created build_dataset.py

Builds a golden dataset named `email-classifier-golden` using `DatasetStore` + `Evaluable`. The dataset contains five hand-labelled test cases covering all four categories and all three priority levels:

| Email theme | Expected category | Expected priority |
|---|---|---|
| Double billing charge | billing | high |
| App crash on large upload | technical | high |
| Password reset question | account | medium |
| Non-profit discount enquiry | general | low |
| Account locked before deadline | account | high |

`expected_output` is a JSON-serialised string containing `category`, `priority`, and a reference `summary`. Run once with `python build_dataset.py` to populate `./pixie_datasets/`.

### 3. Created test_extractor.py

Five `pytest`-style async tests using `assert_pass` and `assert_dataset_pass`:

| Test | What it checks | LLM required? |
|---|---|---|
| `test_output_has_required_keys` | All three keys present | No |
| `test_category_is_valid_enum` | category in allowed set | No |
| `test_priority_is_valid_enum` | priority in allowed set | No |
| `test_summary_is_non_empty` | summary is a non-empty string | No |
| `test_full_structure_pass_threshold` | All four checks, 80 % pass rate | No |
| `test_dataset_category_and_priority` | category + priority match golden set, 80 % | No |

All evaluators are heuristic (no LLM-as-judge) so they work without a second OpenAI key. The app under test still needs `OPENAI_API_KEY` to call GPT-4o-mini.

## Files changed / created

- `project/extractor.py` — added pixie instrumentation (`@px.observe`, `px.init()`, `px.flush()`)
- `project/build_dataset.py` — programmatic dataset builder (NEW)
- `project/test_extractor.py` — eval-based test suite (NEW)

## How to run

```bash
# 1. Build the golden dataset (once)
cd project && python build_dataset.py

# 2. Run tests (requires OPENAI_API_KEY)
pytest test_extractor.py -v
# or
pixie-test test_extractor.py -v
```
