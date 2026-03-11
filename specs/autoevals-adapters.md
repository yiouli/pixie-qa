# Autoevals Adapters — Implementation Spec

## Overview

Pre-made evaluators in `pixie.evals` built on top of the [autoevals](https://github.com/braintrustdata/autoevals) Python package. Each adapter wraps an autoevals `Scorer`, translating between pixie's `Evaluator` protocol (`Evaluable → Evaluation`) and autoevals' `Scorer.eval_async(output, expected, **kwargs) → Score` interface.

This gives pixie users access to a rich library of battle-tested evaluators — heuristic scorers (Levenshtein, ExactMatch, NumericDiff, JSONDiff, ValidJSON), LLM-as-judge classifiers (Factuality, ClosedQA, Battle, Humor, Security, Sql, Summary, Translation, Possible), embedding similarity, moderation, and RAGAS metrics — while keeping the pixie `Evaluator` protocol as the single uniform interface.

---

## Module layout

```
pixie/
  evals/
    scorers.py           # adapter class + all pre-made evaluator factories
```

Tests:

```
tests/
  pixie/
    evals/
      test_scorers.py    # unit tests for adapters
```

---

## Dependency

Add `autoevals` as a **runtime** dependency of the `pixie` package.

```toml
# pyproject.toml  (addition)
dependencies = [
    ...
    "autoevals>=0.0.120",
]
```

---

## 1. Core Adapter: `AutoevalsAdapter`

### Class definition

```python
class AutoevalsAdapter:
    """Wrap an autoevals ``Scorer`` to satisfy the pixie ``Evaluator`` protocol.

    The adapter converts between two worlds:

    - **pixie** — evaluator receives ``Evaluable`` (``eval_input``, ``eval_output``,
      ``eval_metadata``), returns ``Evaluation(score, reasoning, details)``.
    - **autoevals** — scorer receives ``output``, ``expected``, ``**kwargs``,
      returns ``Score(name, score, metadata)``.
    """
```

### Constructor

```python
def __init__(
    self,
    scorer: autoevals.Scorer,
    *,
    expected: Any = _UNSET,
    expected_key: str = "expected",
    input_key: str | None = "input",
    extra_metadata_keys: tuple[str, ...] = (),
    **scorer_kwargs: Any,
) -> None:
```

| Parameter             | Purpose                                                                                                                                             |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `scorer`              | The autoevals `Scorer` instance to delegate to.                                                                                                     |
| `expected`            | Fixed expected value. If not provided, pulled from `evaluable.eval_metadata[expected_key]` at call time. If neither is available, `None` is passed. |
| `expected_key`        | Metadata key to read `expected` from. Default `"expected"`.                                                                                         |
| `input_key`           | If not `None`, `evaluable.eval_input` is passed as this kwarg to the scorer. Default `"input"`. Set to `None` to skip.                              |
| `extra_metadata_keys` | Additional metadata keys to forward as kwargs to the scorer (e.g., `("context", "criteria")`).                                                      |
| `**scorer_kwargs`     | Extra fixed kwargs passed to every `eval_async` call (e.g., `language="Spanish"` for Translation).                                                  |

### `__call__`

```python
async def __call__(
    self,
    evaluable: Evaluable,
    *,
    expected_output: Any = None,
    trace: list[ObservationNode] | None = None,
) -> Evaluation:
```

**Steps:**

1. Extract `output = evaluable.eval_output`.
2. Resolve `expected` (highest priority first):
   - If `expected_output` (call-time) is not `None`, use it.
   - Else if constructor-provided `expected` is set, use it.
   - Else if `expected_key` is in `evaluable.eval_metadata`, use that.
   - Else `None`.
3. Build kwargs:
   - If `input_key` is not `None`, add `{input_key: evaluable.eval_input}`.
   - For each key in `extra_metadata_keys`, if present in `evaluable.eval_metadata`, add it.
   - Merge `scorer_kwargs`.
4. Call `await scorer.eval_async(output=output, expected=expected, **kwargs)`.
5. Convert the returned `Score` to `Evaluation` via `_score_to_evaluation()`.
6. If the scorer raises, return `Evaluation(score=0.0, reasoning=str(exc), details={"error": ...})`.

### Score-to-Evaluation conversion

```python
def _score_to_evaluation(score: autoevals.Score) -> Evaluation:
```

| `Score` field                     | `Evaluation` field     | Mapping                                                                                         |
| --------------------------------- | ---------------------- | ----------------------------------------------------------------------------------------------- |
| `score.score`                     | `evaluation.score`     | `float(score.score)` if not `None`, else `0.0`                                                  |
| `score.metadata.get("rationale")` | `evaluation.reasoning` | If present and non-empty, use as reasoning. Otherwise generate `"{score.name}: {score.score}"`. |
| `score.metadata`                  | `evaluation.details`   | Full metadata dict. Add `{"scorer_name": score.name}`.                                          |

---

## 2. Pre-made Evaluator Factories

Each factory is a thin wrapper that constructs the appropriate autoevals `Scorer` and returns an `AutoevalsAdapter`. Users get named, discoverable evaluators without needing to know autoevals internals.

### Heuristic scorers (no LLM required)

| Factory function                                         | autoevals class                     | Notes                                       |
| -------------------------------------------------------- | ----------------------------------- | ------------------------------------------- |
| `LevenshteinMatch(*, expected=...)`                      | `Levenshtein()`                     | `input_key=None` (no `input` kwarg needed). |
| `ExactMatchEval(*, expected=...)`                        | `ExactMatch()`                      | `input_key=None`.                           |
| `NumericDiffEval(*, expected=...)`                       | `NumericDiff()`                     | `input_key=None`.                           |
| `JSONDiffEval(*, expected=..., string_scorer=...)`       | `JSONDiff(string_scorer=...)`       | `input_key=None`.                           |
| `ValidJSONEval(*, schema=...)`                           | `ValidJSON(schema=...)`             | No `expected` needed. `input_key=None`.     |
| `ListContainsEval(*, expected=..., pairwise_scorer=...)` | `ListContains(pairwise_scorer=...)` | `input_key=None`.                           |

### Embedding scorer

| Factory function                                                              | autoevals class                                          | Notes             |
| ----------------------------------------------------------------------------- | -------------------------------------------------------- | ----------------- |
| `EmbeddingSimilarityEval(*, expected=..., prefix=..., model=..., client=...)` | `EmbeddingSimilarity(prefix=..., model=..., client=...)` | `input_key=None`. |

### LLM-as-judge scorers (require OpenAI / proxy)

| Factory function                                                        | autoevals class                      | Extra kwargs                                                            |
| ----------------------------------------------------------------------- | ------------------------------------ | ----------------------------------------------------------------------- |
| `FactualityEval(*, expected=..., model=..., client=...)`                | `Factuality(model=..., client=...)`  | `input_key="input"` (sends `eval_input`).                               |
| `ClosedQAEval(*, expected=..., model=..., client=...)`                  | `ClosedQA(model=..., client=...)`    | `input_key="input"`, `extra_metadata_keys=("criteria",)`.               |
| `BattleEval(*, expected=..., model=..., client=...)`                    | `Battle(model=..., client=...)`      | `input_key="instructions"` (maps `eval_input` to `instructions` kwarg). |
| `HumorEval(*, model=..., client=...)`                                   | `Humor(model=..., client=...)`       | No `expected` needed. `input_key=None`.                                 |
| `SecurityEval(*, model=..., client=...)`                                | `Security(model=..., client=...)`    | `input_key="instructions"`.                                             |
| `SqlEval(*, expected=..., model=..., client=...)`                       | `Sql(model=..., client=...)`         | `input_key="input"`.                                                    |
| `SummaryEval(*, expected=..., model=..., client=...)`                   | `Summary(model=..., client=...)`     | `input_key="input"`.                                                    |
| `TranslationEval(*, expected=..., language=..., model=..., client=...)` | `Translation(model=..., client=...)` | `input_key="input"`, passes `language` as scorer kwarg.                 |
| `PossibleEval(*, model=..., client=...)`                                | `Possible(model=..., client=...)`    | `input_key="input"`.                                                    |

### Moderation

| Factory function                               | autoevals class                         | Notes                            |
| ---------------------------------------------- | --------------------------------------- | -------------------------------- |
| `ModerationEval(*, threshold=..., client=...)` | `Moderation(threshold=..., client=...)` | No `expected`. `input_key=None`. |

### RAGAS metrics

| Factory function                                                  | autoevals class                 | Notes                                                    |
| ----------------------------------------------------------------- | ------------------------------- | -------------------------------------------------------- |
| `ContextRelevancyEval(*, expected=..., context=..., client=...)`  | `ContextRelevancy(client=...)`  | `input_key="input"`, `extra_metadata_keys=("context",)`. |
| `FaithfulnessEval(*, context=..., client=...)`                    | `Faithfulness(client=...)`      | `input_key="input"`, `extra_metadata_keys=("context",)`. |
| `AnswerRelevancyEval(*, context=..., client=...)`                 | `AnswerRelevancy(client=...)`   | `input_key="input"`, `extra_metadata_keys=("context",)`. |
| `AnswerCorrectnessEval(*, expected=..., context=..., client=...)` | `AnswerCorrectness(client=...)` | `input_key="input"`, `extra_metadata_keys=("context",)`. |

---

## 3. Public API

All pre-made evaluators are exported from `pixie.evals`:

```python
# pixie/evals/__init__.py  (additions)
from pixie.evals.scorers import (
    AutoevalsAdapter,
    AnswerCorrectnessEval,
    AnswerRelevancyEval,
    BattleEval,
    ClosedQAEval,
    ContextRelevancyEval,
    EmbeddingSimilarityEval,
    ExactMatchEval,
    FactualityEval,
    FaithfulnessEval,
    HumorEval,
    JSONDiffEval,
    LevenshteinMatch,
    ListContainsEval,
    ModerationEval,
    NumericDiffEval,
    PossibleEval,
    SecurityEval,
    SqlEval,
    SummaryEval,
    TranslationEval,
    ValidJSONEval,
)
```

---

## 4. Usage Examples

### Heuristic (no LLM)

```python
from pixie.evals import evaluate, LevenshteinMatch

evaluator = LevenshteinMatch(expected="hello world")
result = await evaluate(evaluator, evaluable)
print(result.score)      # e.g. 0.91
print(result.reasoning)  # "Levenshtein: 0.91"
```

### LLM-as-judge

```python
from openai import AsyncOpenAI
from autoevals import init
from pixie.evals import evaluate, FactualityEval

init(AsyncOpenAI())  # one-time global setup

evaluator = FactualityEval(expected="Paris is the capital of France")
result = await evaluate(evaluator, evaluable)
print(result.score)      # 1.0
print(result.reasoning)  # CoT rationale from the LLM judge
```

### With run_and_evaluate

```python
from pixie.evals import run_and_evaluate, ClosedQAEval, last_llm_call

evaluator = ClosedQAEval(expected="42")
result = await run_and_evaluate(
    evaluator=evaluator,
    runnable=my_app,
    input="What is the answer to life?",
    from_trace=last_llm_call,
)
```

### With assert_pass

```python
from pixie.evals import assert_pass, FactualityEval, LevenshteinMatch

await assert_pass(
    evaluators=[FactualityEval(expected="Paris"), LevenshteinMatch(expected="Paris")],
    runnable=my_qa_app,
    inputs=["What is the capital of France?"],
)
```

### Generic adapter for any autoevals scorer

```python
from autoevals.llm import LLMClassifier
from pixie.evals import AutoevalsAdapter

custom_scorer = LLMClassifier(
    name="toxicity",
    prompt_template="Rate if this text is toxic: {{output}}",
    choice_scores={"toxic": 0, "not_toxic": 1},
)
evaluator = AutoevalsAdapter(custom_scorer, input_key=None)
result = await evaluate(evaluator, evaluable)
```

---

## 5. Error Handling

- If `scorer.eval_async()` raises, the adapter catches the exception and returns `Evaluation(score=0.0, reasoning=str(exc), details={"error": type(exc).__name__, "traceback": ...})`.
- If `score.score` is `None` (autoevals "skipped" semantics), map to `score=0.0` with reasoning `"Evaluation skipped (score is None)"`.
- Malformed `score.metadata` (not a dict or missing) → use empty dict.

---

## 6. Testing Strategy

All tests use **mocked** autoevals scorers — no real LLM calls. Tests verify:

1. **Score → Evaluation mapping**: score values, None handling, reasoning extraction, metadata passthrough.
2. **Evaluable → scorer kwargs mapping**: `eval_output` → `output`, `eval_input` → `input`, metadata key extraction, fixed `expected`.
3. **Error handling**: scorer raises → `Evaluation(score=0.0, ...)`.
4. **Each pre-made factory**: correct autoevals class instantiated, correct adapter configuration (input_key, extra_metadata_keys, etc.).

Test file: `tests/pixie/evals/test_scorers.py`.
