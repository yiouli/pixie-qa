# Autoevals Adapters

## What changed

Added pre-made evaluators in `pixie.evals` built on top of the
[autoevals](https://github.com/braintrustdata/autoevals) Python package.
The `AutoevalsAdapter` class bridges autoevals' `Scorer` interface
(`output, expected, **kwargs → Score`) to pixie's `Evaluator` protocol
(`Evaluable → Evaluation`).

22 evaluator factories are provided out of the box:

- **Heuristic**: `LevenshteinMatch`, `ExactMatchEval`, `NumericDiffEval`,
  `JSONDiffEval`, `ValidJSONEval`, `ListContainsEval`
- **Embedding**: `EmbeddingSimilarityEval`
- **LLM-as-judge**: `FactualityEval`, `ClosedQAEval`, `BattleEval`,
  `HumorEval`, `SecurityEval`, `SqlEval`, `SummaryEval`,
  `TranslationEval`, `PossibleEval`
- **Moderation**: `ModerationEval`
- **RAGAS**: `ContextRelevancyEval`, `FaithfulnessEval`,
  `AnswerRelevancyEval`, `AnswerCorrectnessEval`

## Files affected

| File                                | Change                                                                 |
| ----------------------------------- | ---------------------------------------------------------------------- |
| `pixie/evals/scorers.py`            | New module — adapter class and all factory functions                   |
| `pixie/evals/__init__.py`           | Re-exports all new evaluators                                          |
| `tests/pixie/evals/test_scorers.py` | New test module — 42 tests                                             |
| `pyproject.toml`                    | Added `autoevals` runtime dependency; mypy override for untyped import |
| `specs/autoevals-adapters.md`       | New spec document                                                      |
| `README.md`                         | Added pre-made evaluators section and spec link                        |

## Migration notes

- `autoevals` is now a runtime dependency of the `pixie` package. Any
  environment that installs `pixie` will also pull in `autoevals` and its
  transitive dependencies (`chevron`, `polyleven`, `pyyaml`, etc.).
- No breaking changes to existing APIs. All new symbols are additive.
