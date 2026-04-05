# Step 4: Define Evaluators

**Why this step**: With the app instrumented and a utility function ready, you now map each eval criterion to a concrete evaluator — implementing custom ones where needed — so the dataset (Step 5) can reference them by name.

---

## 4a. Map criteria to evaluators

**Every eval criterion from Step 1c — including any dimensions specified by the user in the prompt — must have a corresponding evaluator.** If the user asked for "factuality, completeness, and bias," you need three evaluators (or a multi-criteria evaluator that covers all three). Do not silently drop any requested dimension.

For each eval criterion, decide how to evaluate it:

- **Can it be checked with a built-in evaluator?** (factual correctness → `Factuality`, exact match → `ExactMatch`, RAG faithfulness → `Faithfulness`)
- **Does it need a custom evaluator?** Most app-specific criteria do — use `create_llm_evaluator` with a prompt that operationalizes the criterion.
- **Is it universal or case-specific?** Universal criteria apply to all dataset items. Case-specific criteria apply only to certain rows.

For open-ended LLM text, **never** use `ExactMatch` — LLM outputs are non-deterministic.

`AnswerRelevancy` is **RAG-only** — it requires a `context` value in the trace. Returns 0.0 without it. For general relevance without RAG, use `create_llm_evaluator` with a custom prompt.

## 4b. Implement custom evaluators

If any criterion requires a custom evaluator, implement it now. Place custom evaluators in `pixie_qa/evaluators.py` (or a sub-module if there are many).

### `create_llm_evaluator` factory

Use when the quality dimension is domain-specific and no built-in evaluator fits.

The return value is a **ready-to-use evaluator instance**. Assign it to a module-level variable — `pixie test` will import and use it directly (no class wrapper needed):

```python
from pixie import create_llm_evaluator

concise_voice_style = create_llm_evaluator(
    name="ConciseVoiceStyle",
    prompt_template="""
    You are evaluating whether this response is concise and phone-friendly.

    Input: {eval_input}
    Response: {eval_output}

    Score 1.0 if the response is concise (under 3 sentences), directly addresses
    the question, and uses conversational language suitable for a phone call.
    Score 0.0 if it's verbose, off-topic, or uses written-style formatting.
    """,
)
```

Reference the evaluator in your dataset JSON by its `filepath:callable_name` reference (e.g., `"pixie_qa/evaluators.py:concise_voice_style"`).

**How template variables work**: `{eval_input}`, `{eval_output}`, `{expected_output}` are the only placeholders. Each is replaced with a string representation of the corresponding `Evaluable` field — if the field is a dict or list, it becomes a JSON string. The LLM judge sees the full serialized value.

**Rules**:

- **Only `{eval_input}`, `{eval_output}`, `{expected_output}`** — no nested access like `{eval_input[key]}` (this will crash with a `TypeError`)
- **Keep templates short and direct** — the system prompt already tells the LLM to return `Score: X.X`. Your template just needs to present the data and define the scoring criteria.
- **Don't instruct the LLM to "parse" or "extract" data** — just present the values and state the criteria. The LLM can read JSON naturally.

**Non-RAG response relevance** (instead of `AnswerRelevancy`):

```python
response_relevance = create_llm_evaluator(
    name="ResponseRelevance",
    prompt_template="""
    You are evaluating whether a customer support response is relevant and helpful.

    Input: {eval_input}
    Response: {eval_output}
    Expected: {expected_output}

    Score 1.0 if the response directly addresses the question and meets expectations.
    Score 0.5 if partially relevant but misses important aspects.
    Score 0.0 if off-topic, ignores the question, or contradicts expectations.
    """,
)
```

### Manual custom evaluator

Custom evaluators can be **sync or async functions**. Assign them to module-level variables in `pixie_qa/evaluators.py`:

```python
from pixie import Evaluation, Evaluable

def my_evaluator(evaluable: Evaluable, *, trace=None) -> Evaluation:
    score = 1.0 if "expected pattern" in str(evaluable.eval_output) else 0.0
    return Evaluation(score=score, reasoning="...")
```

Reference by `filepath:callable_name` in the dataset: `"pixie_qa/evaluators.py:my_evaluator"`.

## 4c. Produce the evaluator mapping artifact

Write the criterion-to-evaluator mapping to `pixie_qa/05-evaluator-mapping.md`. This artifact bridges between the eval criteria (Step 1c) and the dataset (Step 5).

**CRITICAL**: Use the exact evaluator names as they appear in the `evaluators.md` reference — built-in evaluators use their short name (e.g., `Factuality`, `ClosedQA`), and custom evaluators use `filepath:callable_name` format (e.g., `pixie_qa/evaluators.py:ConciseVoiceStyle`).

### Template

```markdown
# Evaluator Mapping

## Built-in evaluators used

| Evaluator name | Criterion it covers | Applies to                 |
| -------------- | ------------------- | -------------------------- |
| Factuality     | Factual accuracy    | All items                  |
| ClosedQA       | Answer correctness  | Items with expected_output |

## Custom evaluators

| Evaluator name                           | Criterion it covers | Applies to | Source file            |
| ---------------------------------------- | ------------------- | ---------- | ---------------------- |
| pixie_qa/evaluators.py:ConciseVoiceStyle | Phone-friendly tone | All items  | pixie_qa/evaluators.py |

## Applicability summary

- **Dataset-level defaults** (apply to all items): Factuality, pixie_qa/evaluators.py:ConciseVoiceStyle
- **Item-specific** (apply to subset): ClosedQA (only items with expected_output)
```

## Output

- Custom evaluator implementations in `pixie_qa/evaluators.py` (if any custom evaluators needed)
- `pixie_qa/05-evaluator-mapping.md` — the criterion-to-evaluator mapping

---

> **Evaluator selection guide**: See `evaluators.md` for the full evaluator catalog, selection guide (which evaluator for which output type), and `create_llm_evaluator` reference.
>
> **If you hit an unexpected error** when implementing evaluators (import failures, API mismatch), read `evaluators.md` for the authoritative evaluator reference and `instrumentation-api.md` for API details before guessing at a fix.
