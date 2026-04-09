---
title: Eval Analysis Revamp — Deterministic Data Prep with Trace Capture
version: 1.0
date_created: 2026-04-09
owner: pixie-qa
tags: [design, process, instrumentation]
---

# Introduction

Rewrite `pixie analyze` from an OpenAI-dependent LLM call into deterministic data preparation (statistics, failure clusters, trace summaries — no LLM, no API key). Add always-on LLM trace capture to `pixie test` (per-entry JSONL files, reusing existing trace infrastructure). Create skill v30 with a structured analysis framework so the coding agent performs root-cause analysis using the rich data.

## 1. Purpose & Scope

**Purpose:** Replace the current `pixie analyze` command — which calls the OpenAI API to generate a markdown analysis of test results — with a fully deterministic pipeline that computes statistics, clusters failures, and formats trace data into structured markdown. Separately, enhance `pixie test` to capture LLM call traces for every dataset entry automatically.

**Scope:**

- `pixie/harness/trace_capture.py` — new module for per-entry LLM span collection.
- `pixie/cli/analyze_command.py` — major rewrite to remove OpenAI dependency.
- `pixie/cli/test_command.py` — integration of trace capture initialization.
- `pixie/harness/run_result.py` — add `trace_file` field to `EntryResult`.
- `pixie/harness/runner.py` — write per-entry JSONL after completion.
- `skill_versions/v30/` — new skill version with structured analysis framework.
- Tests for all new and modified modules.

**Out of scope:**

- UI/frontend changes for trace visualization.
- Changes to `pixie trace` command.
- Changes to evaluator implementations or scorecard HTML.

**Intended audience:** Developers working on the pixie-qa package and the eval-driven-dev skill.

**Assumptions:**

- The existing OTel-based instrumentation infrastructure (`enable_llm_tracing`, `InstrumentationHandler`, `LLMSpan`) is stable and reusable.
- Trace capture has zero overhead when no OpenInference instrumentors are installed.

## 2. Definitions

| Term                       | Definition                                                                                                   |
| -------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Entry**                  | A single row in a dataset JSON file — one invocation of the runnable plus its evaluations.                   |
| **EntryResult**            | The result dataclass for one entry: input, output, expected output, evaluations, and (new) trace file path.  |
| **DatasetResult**          | Aggregated results for all entries in one dataset.                                                           |
| **RunResult**              | Top-level container holding metadata and all DatasetResults for a test run.                                  |
| **JSONL**                  | JSON Lines format — one JSON object per line.                                                                |
| **Trace file**             | A JSONL file containing serialized `LLMSpanLog` records for all LLM calls made during one entry's execution. |
| **Failure cluster**        | A group of entries that failed the same set of evaluators — used to identify systemic patterns.              |
| **TraceCaptureHandler**    | An `InstrumentationHandler` subclass that collects `LLMSpan` objects keyed by `trace_id`.                    |
| **Deterministic analysis** | Analysis computed from data alone (statistics, groupings, formatting) — no LLM calls, no API keys.           |

## 3. Requirements, Constraints & Guidelines

### Trace Capture (Phase 2)

- **REQ-001**: `pixie test` must call `enable_llm_tracing()` once at test run start, before running any entries.
- **REQ-002**: A `TraceCaptureHandler` must collect `LLMSpan` objects in memory, keyed by `trace_id`, during entry execution.
- **REQ-003**: After each entry completes, all collected spans for that entry must be written to `{result_dir}/traces/entry-{i}.jsonl` (zero-indexed).
- **REQ-004**: Each line in the JSONL trace file must be a serialized `LLMSpanLog` (reusing the existing model from `pixie.instrumentation.models`), extended with timing and token fields: `input_tokens`, `output_tokens`, `duration_ms`, `started_at`, `ended_at`.
- **REQ-005**: `EntryResult` must gain an optional `trace_file: str | None` field. When traces are captured, this field holds the relative path to the JSONL file (e.g. `traces/entry-0.jsonl`).
- **REQ-006**: Serialization (`save_test_result`) and deserialization (`load_test_result`) must round-trip the `trace_file` field in `result.json`.
- **REQ-007**: When no instrumentors are installed (no LLM calls detected), the trace file must still be written but may be empty (zero lines). The `trace_file` field must still be populated.
- **REQ-008**: The `traces/` directory must be created inside `{result_dir}` alongside `result.json`.

### Deterministic Analysis (Phase 3)

- **REQ-009**: `pixie analyze` must not import or call any LLM client library (OpenAI, Anthropic, etc.). The entire analysis must be computed deterministically from the test results and trace files.
- **REQ-010**: For each dataset, `pixie analyze` must produce a `dataset-{i}.md` file containing: (a) Overview section with pass/fail counts, (b) Per-Evaluator Statistics table (pass rate, min/max/mean/stddev scores), (c) Failure Clusters section grouping entries by their set of failed evaluators, (d) Trace Summary table (models used, total tokens, total latency, errors) per entry, (e) Entry Details with per-entry evaluator scores and trace data.
- **REQ-011**: `pixie analyze` must produce a `summary.md` file containing cross-dataset systemic patterns: evaluator consistency, common failure modes, aggregate trace statistics.
- **REQ-012**: The `analyze()` entry point must be synchronous (no `asyncio.run`). All computation is CPU-bound.
- **REQ-013**: `pixie analyze` must not require any environment variables (e.g. `OPENAI_API_KEY`). The only required argument is `test_id`.

### Backward Compatibility

- **CON-001**: Old results without `trace_file` in `result.json` must still load correctly (field defaults to `None`).
- **CON-002**: Old results without a `traces/` directory must still be analyzable — the Trace Summary section is omitted when no trace files exist.
- **CON-003**: The `dataset-{i}.md` output format must be backward compatible — `load_test_result` already reads these files into `DatasetResult.analysis`.

### Skill v30 (Phase 4)

- **REQ-014**: Create `skill_versions/v30/` by copying v29 and updating the analysis/investigation references.
- **REQ-015**: The investigation reference (`6-investigate.md`) must define a structured framework: Read Data Summaries → Failure Root-Cause Classification → Trace-Based Investigation → Evaluator Effectiveness Assessment → Actionable Improvement Plan.
- **REQ-016**: Every finding in the agent's analysis must include mandatory evidence: entry index, evaluator name, score, reasoning quote, and trace data (when available).

### Guidelines

- **GUD-001**: Reuse `LLMSpanLog` from `pixie.instrumentation.models` for trace serialization. Extend it with a new model rather than modifying the existing one if additional fields are needed.
- **GUD-002**: Use `LLMTraceLogger` from `trace_command.py` as a pattern for LLMSpan → LLMSpanLog conversion.
- **GUD-003**: The `TraceCaptureHandler` should use `threading.Lock` for thread safety since OTel spans may arrive from multiple threads.
- **GUD-004**: Output tables should use consistent column widths and alignment for machine parsability.

## 4. Interfaces & Data Contracts

### 4.1 TraceCaptureHandler API

```python
# pixie/harness/trace_capture.py

class TraceCaptureHandler(InstrumentationHandler):
    """Collects LLMSpan objects keyed by trace_id for per-entry trace capture."""

    async def on_llm(self, span: LLMSpan) -> None:
        """Accumulate span under its trace_id."""

    def collect(self, trace_id: str) -> list[LLMSpan]:
        """Remove and return all spans for the given trace_id."""

    def write_entry_traces(
        self,
        trace_id: str,
        output_path: str,
    ) -> int:
        """Write collected spans to a JSONL file. Returns span count."""
```

### 4.2 Extended Trace Log Model

```python
# pixie/instrumentation/models.py — new model

class LLMSpanTrace(BaseModel):
    """Full LLM span record including timing and token data for trace analysis."""
    type: Literal["llm_span_trace"] = "llm_span_trace"
    operation: str | None = None
    provider: str | None = None
    request_model: str | None = None
    response_model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: float = 0.0
    started_at: str | None = None
    ended_at: str | None = None
    input_messages: list[dict[str, Any]] = []
    output_messages: list[dict[str, Any]] = []
    tool_definitions: list[dict[str, Any]] = []
    finish_reasons: list[str] = []
    error_type: str | None = None
```

### 4.3 EntryResult Change

```python
# pixie/harness/run_result.py — updated

@dataclass(frozen=True)
class EntryResult:
    input: JsonValue
    output: JsonValue
    expected_output: JsonValue | None
    description: str | None
    evaluations: list[EvaluationResult]
    trace_file: str | None = None  # NEW — relative path to traces/entry-{i}.jsonl
```

### 4.4 dataset-{i}.md Output Schema

```markdown
# Dataset: {name}

## Overview

- **Entries**: {total} ({passed} passed, {failed} failed)
- **Pass rate**: {rate}%

## Per-Evaluator Statistics

| Evaluator | Pass Rate | Min | Max | Mean | Stddev |
| --------- | --------- | --- | --- | ---- | ------ |
| ...       | ...       | ... | ... | ...  | ...    |

## Failure Clusters

### Cluster: {evaluator_set}

Entries failing: {evaluator_a}, {evaluator_b}

| Entry | Description | Scores | Reasoning |
| ----- | ----------- | ------ | --------- |
| ...   | ...         | ...    | ...       |

## Trace Summary

| Entry | Models | Input Tokens | Output Tokens | Duration (ms) | Errors |
| ----- | ------ | ------------ | ------------- | ------------- | ------ |
| ...   | ...    | ...          | ...           | ...           | ...    |

## Entry Details

### Entry {i}: {description}

- **Status**: PASS/FAIL
- **Input**: {json}
- **Output**: {json}
- **Expected**: {json}

| Evaluator | Score | Pass | Reasoning |
| --------- | ----- | ---- | --------- |
| ...       | ...   | ...  | ...       |

**Trace** ({n} LLM calls):
| # | Model | Tokens (in/out) | Duration | Error |
|---|-------|-----------------|----------|-------|
| ... |
```

### 4.5 summary.md Output Schema

```markdown
# Cross-Dataset Summary

## Aggregate Statistics

- **Total entries**: {n} across {d} datasets
- **Overall pass rate**: {rate}%

## Evaluator Consistency

| Evaluator | Datasets Used | Overall Pass Rate | Min Dataset Rate | Max Dataset Rate |
| --------- | ------------- | ----------------- | ---------------- | ---------------- |
| ...       | ...           | ...               | ...              | ...              |

## Common Failure Patterns

- {pattern_description}

## Aggregate Trace Statistics

- **Total LLM calls**: {n}
- **Models used**: {list}
- **Total tokens**: {in} input, {out} output
- **Total latency**: {ms} ms
```

## 5. Acceptance Criteria

- **AC-001**: Given a `pixie test` run with LLM instrumentors installed, When the run completes, Then `{result_dir}/traces/entry-{i}.jsonl` files exist for each entry and contain valid JSON lines with `LLMSpanTrace` records.
- **AC-002**: Given a `pixie test` run without instrumentors, When the run completes, Then `{result_dir}/traces/entry-{i}.jsonl` files exist but are empty (zero lines).
- **AC-003**: Given `result.json` from a test run, When loaded via `load_test_result()`, Then each `EntryResult.trace_file` contains the relative path (or `None` for old results).
- **AC-004**: Given a test run with both passing and failing entries, When `pixie analyze <test_id>` runs, Then `dataset-{i}.md` contains correct per-evaluator statistics (pass rate, min, max, mean, stddev).
- **AC-005**: Given a test run with entries failing the same evaluators, When `pixie analyze` runs, Then entries are grouped into failure clusters by their set of failed evaluators.
- **AC-006**: Given a test run with trace files, When `pixie analyze` runs, Then the Trace Summary table shows correct models, token counts, latency, and errors per entry.
- **AC-007**: Given a test run without trace files (old results), When `pixie analyze` runs, Then the Trace Summary section is omitted and no error occurs.
- **AC-008**: Given `pixie analyze` runs on a multi-dataset result, When complete, Then `summary.md` exists with cross-dataset evaluator consistency and aggregate statistics.
- **AC-009**: `pixie analyze` completes successfully without `OPENAI_API_KEY` set, without any network calls.
- **AC-010**: All existing tests continue to pass (`uv run pytest`).

## 6. Test Automation Strategy

- **Test Levels**: Unit tests for `TraceCaptureHandler`, `LLMSpanTrace` model, statistics functions, cluster computation, markdown formatting. Integration tests for end-to-end `analyze()` with fixture data.
- **Frameworks**: pytest, pytest fixtures, `monkeypatch` for environment variables, `tmp_path` for file I/O.
- **Test Data Management**: Create minimal `RunResult` fixtures inline; create sample JSONL trace files in `tmp_path`.
- **Coverage Requirements**: All public functions in new/modified modules must have tests.
- **Test Locations**:
  - `tests/pixie/harness/test_trace_capture.py` — TraceCaptureHandler unit tests
  - `tests/pixie/cli/test_analyze_command.py` — rewrite for deterministic analysis tests

### Key Test Cases

1. `TraceCaptureHandler.on_llm()` accumulates spans by trace_id.
2. `TraceCaptureHandler.collect()` removes and returns spans for a trace_id.
3. `TraceCaptureHandler.write_entry_traces()` writes valid JSONL.
4. `EntryResult` serialization/deserialization round-trips `trace_file`.
5. `_build_dataset_summary()` computes correct statistics.
6. `_build_dataset_summary()` groups failures into clusters.
7. `_build_dataset_summary()` includes trace data when available.
8. `_build_dataset_summary()` omits trace section for old results.
9. `_build_cross_dataset_summary()` produces correct aggregate stats.
10. `analyze()` returns 0, writes `dataset-{i}.md` and `summary.md`.
11. `analyze()` returns 1 for nonexistent test_id.

## 7. Rationale & Context

The current `pixie analyze` command requires an `OPENAI_API_KEY` and makes API calls to `gpt-4o-mini` to generate analysis markdown. This has several problems:

1. **Cost and reliability** — every analysis run costs money and can fail on API errors.
2. **Non-determinism** — the same test results produce different analyses each time.
3. **Missing trace data** — the analysis has no visibility into what LLM calls the app actually made (the models used, prompts, token counts, errors).
4. **Agent unfriendly** — the free-form LLM output is not structured for machine parsing by the coding agent.

The revamped approach produces deterministic, structured markdown that a coding agent can reliably parse. Trace capture provides the missing observability data. The skill's investigation framework guides the agent to use this data effectively.

## 8. Dependencies & External Integrations

### Infrastructure Dependencies

- **INF-001**: OpenTelemetry SDK — `TracerProvider`, span context propagation for trace_id association.
- **INF-002**: OpenInference instrumentors — auto-discovered by `enable_llm_tracing()` for capturing LLM calls.

### Technology Platform Dependencies

- **PLT-001**: Python 3.11+ with `from __future__ import annotations`.
- **PLT-002**: Pydantic for model validation and serialization.
- **PLT-003**: `statistics` stdlib module for mean/stdev computation.

### Data Dependencies

- **DAT-001**: `{pixie_root}/results/{test_id}/result.json` — existing test results.
- **DAT-002**: `{result_dir}/traces/entry-{i}.jsonl` — per-entry trace files (produced by Phase 2).

## 9. Examples & Edge Cases

### Example: TraceCaptureHandler usage

```python
handler = TraceCaptureHandler()
# Spans arrive from OTel callback
await handler.on_llm(span_with_trace_id_abc)
await handler.on_llm(span_with_trace_id_abc)
await handler.on_llm(span_with_trace_id_def)

# After entry 0 completes (trace_id=abc):
count = handler.write_entry_traces("abc", "/tmp/results/traces/entry-0.jsonl")
assert count == 2

# After entry 1 completes (trace_id=def):
count = handler.write_entry_traces("def", "/tmp/results/traces/entry-1.jsonl")
assert count == 1
```

### Edge Cases

1. **No LLM calls during entry**: trace file is written but empty (0 lines). Trace Summary shows "0" for all columns.
2. **Entry raises exception**: trace file is still written with whatever spans were captured before the error.
3. **Concurrent entries**: multiple entries run simultaneously under `Semaphore(4)`. `TraceCaptureHandler` uses locking to safely accumulate spans from concurrent trace_ids.
4. **Old result.json without trace_file**: `EntryResult.trace_file` defaults to `None`. Analysis omits trace sections.
5. **Single dataset**: no `summary.md` cross-dataset section (still written but notes "1 dataset — no cross-dataset patterns").

## 10. Validation Criteria

1. `uv run pytest tests/pixie/harness/test_trace_capture.py` — all trace capture tests pass.
2. `uv run pytest tests/pixie/cli/test_analyze_command.py` — all deterministic analysis tests pass.
3. `uv run pytest` — full test suite passes with no regressions.
4. `uv run mypy pixie/` — zero type errors.
5. `uv run ruff check .` — no lint errors.
6. **Manual**: `pixie test tests/manual/datasets/sample-qa.json --no-open` produces `traces/entry-{i}.jsonl` files in the result directory.
7. **Manual**: `pixie analyze <test_id>` produces structured markdown without requiring `OPENAI_API_KEY`.

## 11. Related Specifications / Further Reading

- [specs/instrumentation.md](instrumentation.md) — instrumentation architecture
- [docs/package.md](../docs/package.md) — pixie package API reference
- [pixie/instrumentation/llm_tracing.py](../pixie/instrumentation/llm_tracing.py) — tracing subsystem
