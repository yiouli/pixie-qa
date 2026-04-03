# Test Harness Redesign

## Overview

Currently the recommended way to define and run pixie-test is to create a dataset containing evaluation inputs/outputs, then separately define a test function that defines the evaluators for all the data entries in the dataset. In practice this would require user to manually group the entries in datasets based on their evaluators, e.g. case X that's evaluated on A & B has to be in a separate dataset as Y that's evaluated on A only.

This creates difficulty for user to organize the dataset and force them to think about the test implementation & dataset organization together rather than independently.

So the goal now is to restructure how dataset & test should be defined to streamline user's thought process & workflow.

## New Architecture

The new architecture removes the need for the user to define tests. Instead, they only define evaluators if they need custom ones.

In the dataset, an `evaluators` column (JSON array) is added to each row, so each row can directly specify its evaluators. Built-in evaluator names (e.g. `"Factuality"`) are resolved automatically; custom evaluators use fully qualified names (e.g. `"myapp.evals.Custom"`).

The test harness command takes the dataset path (absolute or relative to the pixie folder) and runs it. It also supports no-argument mode (scan all datasets in the pixie folder) and directory mode (scan all `.json` files recursively).

## Implementation

### Dataset Format

Each item in the dataset JSON can include an `evaluators` field — a JSON array of evaluator names:

```json
{
  "name": "customer-faq",
  "items": [
    {
      "eval_input": { "question": "What is the baggage allowance?" },
      "eval_output": "You may bring one carry-on bag...",
      "expected_output": "You are allowed one bag under 50 pounds...",
      "evaluators": ["Factuality", "ClosedQA"]
    },
    {
      "eval_input": { "question": "How many seats?" },
      "eval_output": "There are 120 seats...",
      "expected_output": "120 seats...",
      "evaluators": ["Factuality"]
    }
  ]
}
```

Built-in evaluator names (no dots) are auto-resolved to `pixie.{Name}`. Custom evaluators use fully qualified names like `"myapp.evals.MyEval"`.

### Built-in Evaluator Names

The `Eval` suffix has been removed from all built-in evaluator factory functions:

- `ExactMatch`, `LevenshteinMatch`, `NumericDiff`, `JSONDiff`, `ValidJSON`, `ListContains`
- `EmbeddingSimilarity`, `Factuality`, `ClosedQA`, `Battle`, `Humor`, `Security`
- `Sql`, `Summary`, `Translation`, `Possible`, `Moderation`
- `ContextRelevancy`, `Faithfulness`, `AnswerRelevancy`, `AnswerCorrectness`

### CLI Usage

```bash
pixie test path/to/dataset.json       # single dataset file
pixie test path/to/dir/               # all datasets in directory tree
pixie test                            # all datasets in pixie folder
```

When the path is a `.json` file or a directory containing `.json` files, the CLI uses dataset-driven mode. When no path is given, it searches the configured `dataset_dir`. Otherwise it falls back to test-file discovery.

### How It Works

1. **Dataset discovery** — `discover_dataset_files(path)` finds `.json` files (single file, directory, or recursive scan).
2. **Entry loading** — `load_dataset_entries(path)` loads the JSON and extracts entries with their evaluator name lists. Items without `evaluators` are skipped.
3. **Name resolution** — `resolve_evaluator_name(name)` maps bare names to `pixie.{Name}` for built-ins, passes through FQNs with dots, and raises `ValueError` for unknown bare names.
4. **Evaluator instantiation** — `_resolve_evaluator(name)` imports and instantiates the evaluator.
5. **Execution** — each entry is evaluated against its own set of evaluators using `evaluate()`. Evaluators per row are non-uniform.
6. **Scorecard** — each dataset produces its own `DatasetScorecard` with a 2D structure: `DatasetEntryResult[]` (one per row), each containing `Evaluation[]` (one per evaluator). The scorecard is saved as an HTML file.

### Key Files

- `pixie/storage/evaluable.py` — `Evaluable` model has `evaluators: list[str] | None` field
- `pixie/evals/dataset_runner.py` — `resolve_evaluator_name()`, `_resolve_evaluator()`, `discover_dataset_files()`, `load_dataset_entries()`, `BUILTIN_EVALUATOR_NAMES`
- `pixie/cli/test_command.py` — `_is_dataset_mode()`, `_run_dataset()`, `_run_dataset_mode()`, three CLI modes (no-arg/dir/file)
- `pixie/evals/scorecard.py` — `DatasetEntryResult`, `DatasetScorecard`, `save_dataset_scorecard()`, `generate_dataset_scorecard_html()`
- `tests/pixie/evals/test_dataset_runner.py` — 31 unit + integration tests
