# Step 5: Build the Dataset

**Why this step**: The dataset is a JSON file that ties together everything from the previous steps — the runnable (Step 3), the evaluators (Step 4), and the use cases (Step 1c) — into concrete test scenarios. At test time, `pixie test` calls the runnable on each item's `eval_input` to produce `eval_output`, then runs the assigned evaluators to score the result.

---

## Understanding eval_input, eval_output, and expected_output

Before building the dataset, understand what these terms mean:

- **eval_input** = application input + data from external dependencies. It's everything the app needs to run a single scenario: the user's request AND the data it would normally fetch from databases, caches, APIs, etc. The run function from Step 3 patches those external dependencies so the data from `eval_input` is fed into the app at runtime. **eval_input is stored in the dataset** — you create it.

- **eval_output** = what the app actually produces when run on an eval_input. **eval_output is NOT stored in the dataset** — it's produced at test time when the runnable calls the real app with your eval_input. You cannot make it up because it must be the app's real response.

- **expected_output** = case-specific evaluation reference. This is the reference that evaluators compare eval_output against. Its meaning depends on the evaluator (could be a factual answer, a quality description, or a set of criteria). **expected_output is stored in the dataset** — you create it by looking at the reference trace's output to understand what the app produces, then writing what a correct output should look like for each scenario.

The reference trace from `pixie_qa/04-reference-trace.md` serves two purposes:

1. **eval_input shape** — the trace's input shows what the observed function received. Every eval_input you create must match this shape exactly (same field names, same types, same nesting).
2. **expected_output guidance** — the trace's output shows what the app actually returned. Use this to understand _what kind of thing_ the app produces, so you can write meaningful expected_output values for your scenarios.

---

## 5a. Derive evaluator assignments from previous artifacts

The eval criteria artifact (`pixie_qa/03-eval-criteria.md`) maps each criterion to the use cases it applies to. The evaluator mapping artifact (`pixie_qa/05-evaluator-mapping.md`) maps each criterion to a concrete evaluator name. Combine these to determine the dataset configuration:

1. **Dataset-level default evaluators**: Criteria marked as applying to "All" use cases in step 1c → their evaluator names (from step 4) go in the top-level `"evaluators"` array.
2. **Item-level evaluators**: Criteria that apply to only a subset of use cases → their evaluator names go in `"evaluators"` on the relevant rows only, using `"..."` to also include the defaults.

This is a mechanical derivation — the hard work of deciding which criteria apply where was done in Steps 1c and 4.

## 5b. Generate eval_input items

**If the user specified a dataset or data source in the prompt** (e.g., a JSON file with research questions, conversation scenarios, or test cases), use it as the basis for your eval_input items. Read the file, adapt each item to match the data shape from the reference trace, and incorporate them into the dataset. Do NOT ignore specified data and fabricate generic alternatives.

**If no dataset was specified**, create eval_input items guided by the reference trace and use cases:

- **Match the reference trace's data shape exactly** — the reference trace shows what the `@observe`-decorated function received as input. Your eval_inputs must have the same field names, types, and nesting depth. This includes both the application input (user message, query) and the external dependency data (customer profiles, retrieved documents, DB records) that the run function patches in.
- **Cover each use case from Step 1c** — each use case should have at least one representative eval_input item, with meaningfully diverse inputs across items.

Each dataset item contains:

- `eval_input`: the made-up input data (application input + external dependency data), matching the reference trace's structure
- `description`: mapped directly from the use case one-liners in `pixie_qa/03-eval-criteria.md` — use the same description text for items representing that use case (or a minor variant if there are multiple items per use case)
- `expected_output`: case-specific expectation text (optional — only for items whose evaluators need a reference to compare against). This is a reference for evaluation, not an exact expected answer.
- `evaluators`: (optional) item-level evaluator names, only needed for items that require **different** evaluators than the dataset defaults (as determined in 5a)

At test time, `eval_output` is produced by the runnable function and is not stored in the dataset itself.

## 5c. Build the dataset JSON file

Create the dataset as a JSON file at `pixie_qa/datasets/<name>.json`. The dataset format includes top-level metadata and an items array.

### Dataset JSON structure

```json
{
  "name": "qa-golden-set",
  "runnable": "pixie_qa/scripts/run_app.py:run_app",
  "evaluators": ["Factuality", "pixie_qa/evaluators.py:ConciseVoiceStyle"],
  "items": [
    {
      "description": "Customer asks about business hours with gold tier account",
      "eval_input": {
        "user_message": "What are your business hours?",
        "customer_profile": {
          "name": "Alice Johnson",
          "account_id": "C100",
          "tier": "gold"
        }
      },
      "expected_output": "Should mention Mon-Fri 9am-5pm and Sat 10am-2pm"
    },
    {
      "description": "Ambiguous change request requiring clarification from basic tier customer",
      "eval_input": {
        "user_message": "I want to change something",
        "customer_profile": {
          "name": "Bob Smith",
          "account_id": "C200",
          "tier": "basic"
        }
      },
      "expected_output": "Should ask for clarification about what to change",
      "evaluators": ["...", "ClosedQA"]
    }
  ]
}
```

### Key fields

- **`runnable`** (required): The `filepath:callable_name` reference to the run function from Step 3 (e.g., `"pixie_qa/scripts/run_app.py:run_app"`). The file path is relative to the project root. This is the function that `pixie test` calls with each item's `eval_input` to produce `eval_output`.
- **`evaluators`** (dataset-level, optional): Default evaluator names applied to every item. These are the evaluators for criteria that apply to ALL use cases, as determined in 5a. Use the **exact names** from `pixie_qa/05-evaluator-mapping.md`.
- **`description`** (per-item, required): Mapped from the use case one-liners in `pixie_qa/03-eval-criteria.md`. For multiple items under the same use case, use the same description or a minor variant distinguishing the specific scenario.
- **`evaluators`** (per-item, optional): Row-level evaluator overrides for items that need case-specific evaluators (as determined in 5a). When present, these **replace** the defaults unless `"..."` is included, which **expands** to all default evaluators.

### Evaluator assignment rules

Use the evaluator mapping from `pixie_qa/05-evaluator-mapping.md` to assign evaluators:

1. **Dataset-level defaults**: Evaluators that apply to ALL items go in the top-level `"evaluators"` array.
2. **Item-level overrides**: Items that need **additional** evaluators beyond the defaults use `"evaluators": ["...", "ExtraEval"]` — the `"..."` expands to all defaults.
3. **Item-level replacements**: Items that need a **completely different** set of evaluators use `"evaluators": ["OnlyThis"]` without `"..."`.
4. **Items using only defaults**: Omit the `"evaluators"` field entirely — they automatically get all dataset defaults.

## 5d. Validate the dataset

After building:

1. **Run validation**:

   ```bash
   uv run pixie dataset validate pixie_qa/datasets/<name>.json
   ```

   This checks:
   - `runnable` is present and resolves to a valid callable
   - Every item has a non-empty `description`
   - Every item resolves to at least one evaluator (from row-level, dataset defaults, or both)
   - All evaluator names resolve to valid evaluator classes

2. **Verify structural constraints** — each eval_input matches the reference trace's schema (same fields, same types)
3. **Verify diversity** — items have meaningfully different inputs, not just minor variations
4. **Verify case-specific expectations** — `expected_output` values are specific and testable, not vague
5. For conversational apps, include items with conversation history

Fix any validation errors and re-run until validation passes.

## Output

`pixie_qa/datasets/<name>.json` — the dataset file.

---

## Dataset Creation Reference

### Crafting eval_input items

Each eval_input must match the **exact data shape** from the reference trace. The reference trace shows what the `@observe`-decorated function received — that's your eval_input shape. It includes both what the user sent (application input) AND what the app fetched from external systems (which the run function from Step 3 patches in).

#### What goes into eval_input

| Data category            | Example                                           | In the reference trace as                           |
| ------------------------ | ------------------------------------------------- | --------------------------------------------------- |
| Application input        | User message, query, request body                 | Function arguments from the user-facing entry point |
| External dependency data | Customer profile, retrieved documents, DB records | Data the run function patches in via mocks          |
| Conversation history     | Previous messages in a chat                       | Prior messages passed into the function             |
| Configuration / context  | Feature flags, session state                      | Additional function arguments                       |

#### Matching the reference trace shape

From the reference trace (`pixie trace last`), note:

1. **Field names** — use the exact same keys (e.g., `user_message` not `message`, `customer_profile` not `profile`)
2. **Types** — if the trace shows a list, use a list; if it shows a nested dict, use a nested dict
3. **Realistic values** — the data should look like something the app would actually receive. Don't use placeholder text like "test input" or "lorem ipsum"

**Example**: If the reference trace shows the function received:

```json
{
  "user_message": "I'd like to reschedule my appointment",
  "customer_profile": {
    "name": "Jane Smith",
    "account_id": "A12345",
    "tier": "premium"
  },
  "conversation_history": [
    { "role": "assistant", "content": "Welcome! How can I help you today?" }
  ]
}
```

Then every eval_input you make up must have `user_message` (string), `customer_profile` (dict with `name`, `account_id`, `tier`), and `conversation_history` (list of message dicts).

### Setting expected_output

`expected_output` is a **reference for evaluation** — its meaning depends on which evaluator will consume it.

#### When to set it

| Scenario                                    | expected_output value                                                                  | Evaluator it pairs with                                   |
| ------------------------------------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| Deterministic answer exists                 | The exact answer: `"Paris"`                                                            | `ExactMatch`, `Factuality`, `ClosedQA`                    |
| Open-ended but has quality criteria         | Description of good output: `"Should mention Saturday hours and be under 2 sentences"` | `create_llm_evaluator` with `{expected_output}` in prompt |
| Truly open-ended, no case-specific criteria | Leave as `"UNSET"` or omit                                                             | Standalone evaluators (`Possible`, `Faithfulness`)        |

#### Universal vs. case-specific criteria

- **Universal criteria** apply to ALL test cases → become dataset-level default evaluators. These don't need expected_output.
- **Case-specific criteria** vary per test case → carry as `expected_output` in the dataset item (e.g., "should mention the caller's Tuesday appointment", "should route to billing").

#### Anti-patterns

- **Don't generate both eval_output and expected_output from the same source.** If they're identical and you use `ExactMatch`, the test is circular and catches zero regressions.
- **Don't use comparison evaluators (`Factuality`, `ClosedQA`, `ExactMatch`) on items without expected_output.** They produce meaningless scores.
- **Don't mix expected_output semantics in one dataset.** If some items use expected_output as a factual answer and others as style guidance, evaluators can't handle both. Use different evaluator assignments per item.

### The cardinal rule

**`eval_output` is always produced at test time by the runnable, never stored in the dataset.** The dataset contains `eval_input` (application input + external dependency data, matching the reference trace's shape), `description` (from the use case one-liners in Step 1c), and optionally `expected_output` (the reference for evaluators to judge against). The runnable produces `eval_output` (application output + captured side-effects) by replaying `eval_input` through the real app.
