# Step 6: Analyze Outcomes

**Why this step**: `pixie test` produced raw scores. Now you analyze those results to understand what they mean — completing pending evaluations, identifying patterns, validating hypotheses, and producing an actionable improvement plan. The analysis is structured in three phases that build on each other: entry-level → dataset-level → action plan.

---

## Result directory structure

After `pixie test`, the result directory looks like:

```
{PIXIE_ROOT}/results/<test_id>/
  meta.json
  dataset-{idx}/
    metadata.json
    entry-{idx}/
      config.json              # evaluators, description, expectation
      eval-input.jsonl         # input data fed to evaluators
      eval-output.jsonl        # output data captured from app
      evaluations.jsonl        # scored + pending evaluations
      trace.jsonl              # LLM call traces
```

Read `meta.json` to find the `<test_id>`. All the data you need for analysis is in this directory.

---

## Writing principles

Every analysis artifact you produce must follow these principles:

- **Data-driven**: Every opinion or statement must be backed by concrete data from the evaluation run. Quote scores, cite entry indices, reference specific eval input/output content. No hand-waving. It is better to write nothing than to write something unsubstantiated.
- **Plain & clear**: Write in plain, clear, simple, and concise language. Avoid jargon. State findings directly.
- **Action-oriented**: Every analysis should contribute to the end goal of concrete improvements to the evaluation pipeline or application. Do not write observations that don't lead somewhere.

---

## Phase 1: Entry-level analysis

Process each dataset entry individually. For each `dataset-{idx}/entry-{idx}/`:

### 1a. Read the entry data

Read these files for the entry:

- `config.json` — what evaluators were configured, the description, the expectation
- `eval-input.jsonl` — what data was fed to the app/evaluators
- `eval-output.jsonl` — what the app produced
- `evaluations.jsonl` — current evaluation results (scored and pending)
- `trace.jsonl` — what LLM calls the app made (if available)

### 1b. Complete pending evaluations

If `evaluations.jsonl` contains entries with `"status": "pending"`, you must grade them:

1. Read the `criteria` field of the pending evaluation
2. Apply the criteria to the entry's eval input, eval output, and trace data
3. Assign a **score** between 0.0 and 1.0:
   - `1.0` — fully meets the criteria
   - `0.5`–`0.9` — partially meets criteria (explain what's missing)
   - `0.0`–`0.4` — does not meet criteria
4. Write a **reasoning** string (1–3 sentences citing specific evidence from the output or trace)
5. Replace the pending entry in `evaluations.jsonl` with the scored result:

**Before** (pending):

```json
{
  "evaluator": "ResponseQuality",
  "status": "pending",
  "criteria": "The response should..."
}
```

**After** (scored):

```json
{
  "evaluator": "ResponseQuality",
  "score": 0.85,
  "reasoning": "Response addresses the main question but omits..."
}
```

**Grading guidelines**:

- Be evidence-based — every score must reference specific output or trace content
- Use the criteria literally — do not expand or reinterpret beyond what's written
- Consider the trace — distinguish between app logic problems and LLM quality issues
- Be calibrated — reserve 1.0 for outputs that genuinely satisfy criteria fully
- Do not penalize LLM non-determinism — different phrasing of a correct answer is not a failure

### 1c. Write entry-level analysis

Write `analysis.md` in the entry directory (`dataset-{idx}/entry-{idx}/analysis.md`). Cover:

1. **What this entry tested** — one sentence from the description/input
2. **Evaluation results** — summarize scores from all evaluators (completed + newly graded)
3. **Test case quality** — does this test case effectively exercise the intended capability? Is the expectation clear and appropriate? Are the evaluators well-suited?
4. **Evaluator quality** — for each evaluator on this entry: is the score reasonable given the output? Would a different input produce a different score (discriminative power)?
5. **Application issues** — any problems surfaced by this test case (wrong output, missing data, unexpected behavior). Cite specific evidence from eval-output and trace.

Keep it concise — typically 10–20 lines per entry.

---

## Phase 2: Dataset-level analysis

After all entries in a dataset are analyzed, produce the dataset-level analysis. Write `analysis.md` in the dataset directory (`dataset-{idx}/analysis.md`).

### 2a. Aggregate the data

Summarize across all entries in the dataset:

- Pass/fail counts and overall pass rate
- Per-evaluator statistics (pass rate, min/max/mean scores)
- Which entries failed which evaluators (failure clusters)

### 2b. Form and validate hypotheses

Come up with **exactly 3 high-confidence hypotheses** across these three dimensions:

1. **Test cases quality** — Does the set of test cases sufficiently and efficiently verify the application's capabilities? Does it cover the important failure modes? Are there blind spots?

2. **Evaluation criteria/evaluator quality** — Do the evaluators have proper granularity and grading to catch real issues? Are there rubber-stamp evaluators (all 1.0)? Are there flaky evaluators (high variance without code changes)? Are criteria too vague or too strict?

3. **Application quality** — Based on the evaluation results, what are the application's strengths and weaknesses? Where does it produce high-quality output? Where does it fail?

For each hypothesis:

- **State the hypothesis** clearly in one sentence
- **Cite the evidence** — entry indices, evaluator names, scores, reasoning quotes, trace data
- **Validate or invalidate** — look at the actual eval input/output data and code to confirm or refute
- **Conclusion** — what action does this hypothesis imply?

It is always possible to produce 3 hypotheses even when the data is limited. If the evaluation data doesn't give a conclusive answer on application quality, that itself is a signal about test case or evaluator gaps.

### 2c. Write the dataset analysis

The dataset `analysis.md` should contain:

1. **Overview** — dataset name, entry count, overall pass rate
2. **Per-evaluator statistics** — table with pass rate, score range, mean
3. **Failure clusters** — entries grouped by failed evaluators (helps find systemic issues)
4. **Hypothesis 1: Test cases** — the hypothesis, evidence, validation, conclusion
5. **Hypothesis 2: Evaluators** — same structure
6. **Hypothesis 3: Application** — same structure

---

## Phase 3: Action plan

After all datasets are analyzed, produce the action plan. Write `action-plan.md` at the test run root (`{PIXIE_ROOT}/results/<test_id>/action-plan.md`).

The action plan synthesizes all dataset analyses into a prioritized, itemized list of improvements. Each item must be specific enough that a coding agent can implement it directly.

### Structure

```markdown
# Action Plan

## Summary

- X datasets analyzed, Y total entries, Z% overall pass rate
- [1-2 sentence high-level assessment]

## Priority 1: [Most impactful improvement]

- **What**: [specific change to make]
- **Why**: [which hypothesis from which dataset, with evidence]
- **Expected impact**: [which entries/evaluators this will improve]
- **How**: [concrete implementation steps]

## Priority 2: [Next improvement]

...

## Priority 3: [Next improvement]

...
```

**Prioritization criteria**:

- Systemic issues (affecting multiple entries/datasets) before isolated ones
- Issues with clear, validated evidence before speculative ones
- Application quality gaps before evaluator refinements before test case additions
- Quick fixes before large refactors

The action plan should have 3–5 items. Each must trace back to a validated hypothesis from Phase 2. Do not include items that are speculative or lack evidence.

---

## Process summary

1. **Phase 1** (per entry): Read data → grade pending evaluations → write `entry-{idx}/analysis.md`
2. **Phase 2** (per dataset): Aggregate → form 3 hypotheses → validate → write `dataset-{idx}/analysis.md`
3. **Phase 3** (per test run): Synthesize → prioritize → write `action-plan.md`

Process entries within a dataset concurrently (using subagents if available). Process phases sequentially — Phase 2 depends on Phase 1 outputs, Phase 3 depends on Phase 2 outputs.
