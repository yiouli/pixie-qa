# Evaluation analysis redesign — per-entry directory structure

## What changed

Reorganized `pixie test` output artifacts from a monolithic `result.json` to a per-entry directory structure. This makes it easier for agents to read and write individual entry data (eval input, eval output, evaluations, analysis) without loading or modifying large monolithic files.

### New on-disk layout

```
results/{test_id}/
  meta.json                           # testId, command, startedAt, endedAt
  dataset-{idx}/
    metadata.json                     # dataset name, datasetPath, runnable
    analysis.md                       # agent writes (Phase 2)
    entry-{idx}/
      config.json                     # description, expectation, evaluators, evalMetadata
      eval-input.jsonl                # one NamedData per line
      eval-output.jsonl               # one NamedData per line
      evaluations.jsonl               # one eval result per line
      trace.jsonl                     # existing trace (written by test_command)
      analysis.md                     # agent writes (Phase 1)
  action-plan.md                      # agent writes (Phase 3)
```

### Model changes

- `EntryResult`: Added `eval_input: list[NamedData]`, `eval_output: list[NamedData]`, `evaluators: list[str]`, `expectation: JsonValue | None`, `eval_metadata: dict[str, JsonValue] | None`. Added backward-compat properties `input`, `output`, `expected_output`.
- `DatasetResult`: Added `dataset_path: str`, `runnable: str`.
- `save_test_result()` now writes directory structure (returns dir path, not JSON file path).
- `load_test_result()` reads from directory structure, auto-discovers dataset/entry dirs.
- `_list_results()` checks for `meta.json` instead of `result.json`.
- `analyze_command._analyze_dataset()` writes to `dataset-{idx}/analysis.md` instead of `dataset-{idx}.md`.

## Files affected

### pixie-qa (code)

- `pixie/harness/run_result.py` — new models, save/load rewrite
- `pixie/harness/runner.py` — `run_dataset()` returns 3-tuple (name, runnable, entries), `evaluate_entry()` populates new fields
- `pixie/cli/test_command.py` — unpacks 3-tuple, dataset-namespaced trace paths
- `pixie/web/app.py` — `api_result()` reads from directory structure, `_list_results()` checks `meta.json`
- `pixie/cli/analyze_command.py` — writes to `dataset-{idx}/analysis.md`

### pixie-qa (tests)

- `tests/pixie/conftest.py` — new `make_entry()` and `make_dataset()` test helpers
- `tests/pixie/eval/test_test_result.py` — rewritten for new directory structure
- `tests/pixie/cli/test_analyze_command.py` — updated to use `make_entry`/`make_dataset` helpers
- `tests/pixie/web/test_app.py` — updated to use `meta.json` instead of `result.json`
- `tests/pixie/eval/test_dataset_runner.py` — updated for 3-tuple `run_dataset()` return

## Migration notes

- `save_test_result()` now returns the result directory path (string) instead of the `result.json` file path
- `run_dataset()` returns `(name, runnable, entries)` instead of `(name, entries)`
- The frontend web API reconstructs the same JSON format from the directory structure, so the scorecard UI is unaffected
- `load_test_result()` auto-discovers `dataset-{idx}/entry-{idx}` directories — no need to know the count upfront
