/** Results panel — sidebar list + result viewer */

import { useState, useEffect, useRef } from "react";
import type {
  ArtifactEntry,
  TestResultData,
  DatasetResultData,
  EntryResultData,
  EvaluationResultData,
  AnyEvaluationData,
} from "../types";
import { isPendingEvaluation } from "../types";
import { SidebarList } from "./SidebarList";
import { MarkdownRenderer } from "./MarkdownRenderer";

interface ResultsPanelProps {
  results: ArtifactEntry[];
  autoSelect?: string | null;
  version?: number;
}

export function ResultsPanel({
  results,
  autoSelect,
  version,
}: ResultsPanelProps) {
  const [selected, setSelected] = useState<string | null>(
    results[0]?.path ?? null,
  );
  const [resultData, setResultData] = useState<TestResultData | null>(null);

  useEffect(() => {
    if (autoSelect && results.some((r) => r.path === autoSelect)) {
      setSelected(autoSelect);
    }
  }, [autoSelect, results]);

  useEffect(() => {
    if (
      selected &&
      !results.some((r) => r.path === selected) &&
      results.length > 0
    ) {
      setSelected(results[0].path);
    } else if (!selected && results.length > 0) {
      setSelected(results[0].path);
    }
  }, [results, selected]);

  useEffect(() => {
    if (!selected) {
      setResultData(null);
      return;
    }
    const testId = selected.replace("results/", "");
    fetch(`/api/result?id=${encodeURIComponent(testId)}`)
      .then((r) => r.json())
      .then((data) => setResultData(data as TestResultData))
      .catch(() => setResultData(null));
  }, [selected, version]);

  return (
    <div className="flex h-full">
      <aside className="w-60 min-w-60 overflow-y-auto border-r border-border bg-surface py-2">
        <SidebarList
          items={results}
          selected={selected}
          onSelect={setSelected}
          emptyMessage="No test results yet"
        />
      </aside>
      <div className="flex-1 overflow-auto p-6">
        {resultData ? (
          <ResultView data={resultData} />
        ) : (
          <div className="flex h-full items-center justify-center font-sans text-base text-ink-muted">
            <p>Select a test result to view</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Analysis Block with summary / detail toggle ─────────────────────

function AnalysisBlock({
  summary,
  detail,
  title,
  emptyMessage,
}: {
  summary?: string;
  detail?: string;
  title: string;
  emptyMessage?: string;
}) {
  const [expanded, setExpanded] = useState(false);

  // Nothing to show at all
  if (!summary && !detail) {
    if (emptyMessage) {
      return (
        <div className="rounded-md border-l-3 border-accent bg-bg-inset px-5 py-4">
          <h3 className="mb-3 text-sm font-semibold text-ink-secondary">
            {title}
          </h3>
          <div className="text-sm text-ink-muted">{emptyMessage}</div>
        </div>
      );
    }
    return null;
  }

  // Only detail (no summary) — show detail directly
  const displayContent = summary ?? detail!;
  const hasDetail = summary && detail;

  return (
    <div className="rounded-md border-l-3 border-accent bg-bg-inset px-5 py-4">
      {title && (
        <h3 className="mb-3 text-sm font-semibold text-ink-secondary">
          {title}
        </h3>
      )}
      <MarkdownRenderer className="analysis-content text-sm leading-relaxed">
        {displayContent}
      </MarkdownRenderer>
      {hasDetail && (
        <details
          className="mt-3"
          open={expanded}
          onToggle={(e) => setExpanded((e.target as HTMLDetailsElement).open)}
        >
          <summary className="cursor-pointer text-xs font-semibold text-accent hover:text-accent-hover select-none">
            {expanded ? "Less details" : "More details"}
          </summary>
          <div className="mt-3 rounded-md border border-border bg-surface px-4 py-3">
            <MarkdownRenderer className="analysis-content text-sm leading-relaxed">
              {detail}
            </MarkdownRenderer>
          </div>
        </details>
      )}
    </div>
  );
}

// ── Test Overview ──────────────────────────────────────────────────

function ResultView({ data }: { data: TestResultData }) {
  const { meta, datasets, actionPlan, actionPlanSummary } = data;

  const startedAt = formatLocalTime(meta.startedAt);
  const endedAt = formatLocalTime(meta.endedAt);
  const duration = computeDuration(meta.startedAt, meta.endedAt);

  return (
    <div className="mx-auto max-w-240">
      {/* Test Overview Card */}
      <div className="mb-5 rounded-lg border border-border bg-surface p-6 shadow-sm">
        <h2 className="mb-4 border-b-2 border-border pb-2.5 font-mono text-sm font-bold uppercase tracking-tight text-ink-secondary">
          Test Run Overview
        </h2>
        <table className="mb-4 w-full border-collapse">
          <tbody>
            <tr>
              <td
                className="border-b border-border px-3 py-2 font-semibold text-ink-secondary"
                style={{ width: "100px" }}
              >
                Command
              </td>
              <td className="border-b border-border px-3 py-2">
                <code className="rounded-sm bg-bg-inset px-1.5 py-0.5 font-mono text-sm text-ink">
                  {meta.command}
                </code>
              </td>
            </tr>
            <tr>
              <td className="border-b border-border px-3 py-2 font-semibold text-ink-secondary">
                Start Time
              </td>
              <td className="border-b border-border px-3 py-2 font-sans text-sm">
                {startedAt}
              </td>
            </tr>
            <tr>
              <td className="border-b border-border px-3 py-2 font-semibold text-ink-secondary">
                End Time
              </td>
              <td className="border-b border-border px-3 py-2 font-sans text-sm">
                {endedAt}
              </td>
            </tr>
            <tr>
              <td className="border-b border-border px-3 py-2 font-semibold text-ink-secondary">
                Duration
              </td>
              <td className="border-b border-border px-3 py-2 font-sans text-sm">
                {duration}
              </td>
            </tr>
          </tbody>
        </table>

        {/* Action Plan (inside overview card) */}
        {(actionPlanSummary || actionPlan) && (
          <div className="mt-4">
            <AnalysisBlock
              summary={actionPlanSummary}
              detail={actionPlan}
              title="Action Plan"
            />
          </div>
        )}
      </div>

      {datasets.map((ds) => (
        <DatasetSection key={ds.dataset} dataset={ds} />
      ))}
    </div>
  );
}

// ── Per-Dataset Section ──────────────────────────────────────────────

function DatasetSection({ dataset }: { dataset: DatasetResultData }) {
  const passed = dataset.entries.filter((e) => {
    const completed = e.evaluations.filter((ev) => !isPendingEvaluation(ev));
    return completed.every(
      (ev) => !isPendingEvaluation(ev) && ev.score >= SCORE_FAIL_THRESHOLD,
    );
  }).length;
  const total = dataset.entries.length;
  const pendingCount = dataset.entries.reduce(
    (acc, e) => acc + e.evaluations.filter(isPendingEvaluation).length,
    0,
  );
  const allPass = passed === total;

  return (
    <section className="mb-5 rounded-lg border border-border bg-surface p-6 shadow-sm">
      <div className="mb-4 flex items-center gap-3">
        <h2 className="font-mono text-lg font-bold">{dataset.dataset}</h2>
        <span
          className={`text-xl font-bold ${allPass ? "text-pass" : "text-fail"}`}
        >
          {passed} passed
          {pendingCount > 0 && (
            <span className="text-info"> ({pendingCount} pending)</span>
          )}{" "}
          of {total} total
        </span>
      </div>

      {/* Dataset metadata (app input) */}
      {(dataset.runnable || dataset.datasetPath) && (
        <div className="mb-4 flex flex-wrap gap-x-6 gap-y-1 text-xs text-ink-muted">
          {dataset.runnable && (
            <span>
              <span className="font-semibold text-ink-secondary">
                Runnable:
              </span>{" "}
              <code className="rounded-sm bg-bg-inset px-1 py-0.5 font-mono">
                {dataset.runnable}
              </code>
            </span>
          )}
          {dataset.datasetPath && (
            <span>
              <span className="font-semibold text-ink-secondary">Dataset:</span>{" "}
              <code className="rounded-sm bg-bg-inset px-1 py-0.5 font-mono">
                {dataset.datasetPath}
              </code>
            </span>
          )}
        </div>
      )}

      {/* Analysis section */}
      <div className="mb-5">
        <AnalysisBlock
          summary={dataset.analysisSummary}
          detail={dataset.analysis}
          title="Analysis &amp; Recommendations"
          emptyMessage="No analysis yet."
        />
      </div>

      {/* Entries table */}
      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th className="border-b-2 border-border px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-ink-secondary">
              Scenario
            </th>
            <th className="border-b-2 border-border px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-ink-secondary">
              Result
            </th>
            <th className="border-b-2 border-border px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-ink-secondary">
              Evaluations
            </th>
            <th className="border-b-2 border-border px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-ink-secondary">
              Details
            </th>
          </tr>
        </thead>
        <tbody>
          {dataset.entries.map((entry, i) => (
            <EntryRow key={i} entry={entry} />
          ))}
        </tbody>
      </table>
    </section>
  );
}

// ── Score tier helper ──────────────────────────────────────────────────

type ScoreTier = "pass" | "warn" | "fail";

/** Score below this threshold is a fail. */
const SCORE_FAIL_THRESHOLD = 0.5;
/** Score at or below this threshold (but passing) shows a warning. */
const SCORE_WARN_THRESHOLD = 0.6;

/** Classify a score into pass / warn / fail tier. */
function scoreTier(score: number): ScoreTier {
  if (score < SCORE_FAIL_THRESHOLD) return "fail";
  if (score <= SCORE_WARN_THRESHOLD) return "warn";
  return "pass";
}

/** Sort evaluations by ascending score, with pending evaluations at the end. */
function sortEvaluationsForDisplay(
  evaluations: AnyEvaluationData[],
): AnyEvaluationData[] {
  return evaluations
    .map((evaluation, index) => ({ evaluation, index }))
    .sort((a, b) => {
      const aPending = isPendingEvaluation(a.evaluation);
      const bPending = isPendingEvaluation(b.evaluation);

      if (aPending && bPending) return a.index - b.index;
      if (aPending) return 1;
      if (bPending) return -1;

      if (
        !isPendingEvaluation(a.evaluation) &&
        !isPendingEvaluation(b.evaluation)
      ) {
        const scoreDiff = a.evaluation.score - b.evaluation.score;
        if (scoreDiff !== 0) return scoreDiff;
      }

      return a.index - b.index;
    })
    .map(({ evaluation }) => evaluation);
}

/** Tailwind classes for pill border/text by tier. */
function pillBaseClasses(tier: ScoreTier): string {
  switch (tier) {
    case "pass":
      return "border-pass-border text-pass";
    case "warn":
      return "border-warn-border text-warn";
    case "fail":
      return "border-fail-border text-fail";
  }
}

/** Faint tinted fill shown on hover/focus, when popover is closed. */
function pillHoverFillClasses(tier: ScoreTier): string {
  switch (tier) {
    case "pass":
      return "hover:border-pass hover:bg-pass/12 focus-visible:border-pass focus-visible:bg-pass/12";
    case "warn":
      return "hover:border-warn hover:bg-warn/12 focus-visible:border-warn focus-visible:bg-warn/12";
    case "fail":
      return "hover:border-fail hover:bg-fail/12 focus-visible:border-fail focus-visible:bg-fail/12";
  }
}

/** Stronger fill shown while the evaluator popover is open. */
function pillOpenFillClasses(tier: ScoreTier): string {
  switch (tier) {
    case "pass":
      return "border-pass bg-pass text-white";
    case "warn":
      return "border-warn bg-warn text-white";
    case "fail":
      return "border-fail bg-fail text-white";
  }
}

/** Tailwind classes for the solid score badge by tier. */
function badgeClasses(tier: ScoreTier): string {
  switch (tier) {
    case "pass":
      return "bg-pass text-white";
    case "warn":
      return "bg-warn text-white";
    case "fail":
      return "bg-fail text-white";
  }
}

// ── Evaluator Pill with Popover ──────────────────────────────────────

function EvalPill({ evaluation }: { evaluation: AnyEvaluationData }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function handleEscape(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  if (isPendingEvaluation(evaluation)) {
    return (
      <div className="relative" ref={ref}>
        <button
          type="button"
          className={`inline-flex items-center gap-1 cursor-pointer rounded-pill border border-info-border px-3 py-1 text-xs font-bold tracking-wide text-info transition-colors hover:border-info hover:bg-info/12 focus-visible:border-info focus-visible:bg-info/12`}
          onClick={() => setOpen(!open)}
          aria-expanded={open}
        >
          <svg
            className="h-3 w-3"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="8" cy="8" r="6.25" />
            <path d="M8 4.5V8l2.5 1.5" />
          </svg>
          {evaluation.evaluator}
        </button>
        {open && (
          <div className="absolute left-0 top-full z-20 mt-1.5 w-72 rounded-md border border-border bg-surface p-4 shadow-lg animate-fade-in">
            <div className="mb-2 flex items-center justify-between">
              <span className="font-mono text-xs font-bold text-ink">
                {evaluation.evaluator}
              </span>
              <span className="rounded-pill bg-info px-2 py-0.5 text-xs font-bold text-white">
                Pending
              </span>
            </div>
            <p className="m-0 text-xs leading-relaxed text-ink-secondary">
              {evaluation.criteria}
            </p>
          </div>
        )}
      </div>
    );
  }

  const tier = scoreTier(evaluation.score);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        className={`inline-block cursor-pointer rounded-pill border px-3 py-1 text-xs font-bold tracking-wide transition-colors ${pillBaseClasses(tier)} ${open ? pillOpenFillClasses(tier) : pillHoverFillClasses(tier)}`}
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        {evaluation.evaluator}
      </button>
      {open && (
        <div className="absolute left-0 top-full z-20 mt-1.5 w-72 rounded-md border border-border bg-surface p-4 shadow-lg animate-fade-in">
          <div className="mb-2 flex items-center justify-between">
            <span className="font-mono text-xs font-bold text-ink">
              {evaluation.evaluator}
            </span>
            <span
              className={`rounded-pill px-2 py-0.5 text-xs font-bold ${badgeClasses(tier)}`}
            >
              {evaluation.score.toFixed(2)}
            </span>
          </div>
          {evaluation.reasoning && (
            <p className="m-0 text-xs leading-relaxed text-ink-secondary">
              {evaluation.reasoning}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Entry Row ──────────────────────────────────────────────────

function EntryRow({ entry }: { entry: EntryResultData }) {
  const [detailOpen, setDetailOpen] = useState(false);
  const sortedEvaluations = sortEvaluationsForDisplay(entry.evaluations);
  const completed = entry.evaluations.filter(
    (ev): ev is EvaluationResultData => !isPendingEvaluation(ev),
  );
  const allPass = completed.every((ev) => ev.score >= SCORE_FAIL_THRESHOLD);
  const hasWarning =
    allPass && completed.some((ev) => ev.score <= SCORE_WARN_THRESHOLD);

  const description = entry.description || summarizeInput(entry.input);

  // Row-level badge: FAIL > WARN > PASS
  const rowTier: ScoreTier = !allPass ? "fail" : hasWarning ? "warn" : "pass";

  return (
    <>
      <tr
        className={
          rowTier === "fail"
            ? "bg-fail-bg"
            : rowTier === "warn"
              ? "bg-warn-bg"
              : "bg-transparent"
        }
      >
        <td className="max-w-75 border-b border-border px-3 py-2.5 align-middle font-sans text-sm">
          {description}
        </td>
        <td className="border-b border-border px-3 py-2.5 align-middle">
          <span
            className={`inline-block rounded-pill px-3 py-1 text-xs font-bold tracking-wide ${badgeClasses(rowTier)}`}
          >
            {rowTier === "fail" ? "FAIL" : rowTier === "warn" ? "WARN" : "PASS"}
          </span>
        </td>
        <td className="border-b border-border px-3 py-2.5 align-middle">
          <div className="flex flex-wrap gap-1.5">
            {sortedEvaluations.map((ev, i) => (
              <EvalPill key={i} evaluation={ev} />
            ))}
          </div>
        </td>
        <td className="border-b border-border px-3 py-2.5 align-middle">
          <button
            type="button"
            className="border-none bg-transparent p-0 text-sm text-accent underline hover:text-accent-hover"
            onClick={() => setDetailOpen(true)}
          >
            details
          </button>
        </td>
      </tr>
      {detailOpen && (
        <EvalDetailModal entry={entry} onClose={() => setDetailOpen(false)} />
      )}
    </>
  );
}

// ── Eval Detail Modal ──────────────────────────────────────────────────

function EvalDetailModal({
  entry,
  onClose,
}: {
  entry: EntryResultData;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-30 flex items-center justify-center bg-overlay p-6 animate-fade-in"
      onClick={onClose}
    >
      <div
        className="relative max-h-[80vh] w-full max-w-160 overflow-y-auto rounded-lg bg-surface p-7 shadow-lg animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          className="absolute right-4 top-4 flex h-8 w-8 items-center justify-center rounded-pill border-none bg-border text-lg leading-none transition-colors hover:bg-border-strong"
          onClick={onClose}
        >
          ✕
        </button>
        <h2 className="mb-4 font-mono text-base font-bold">
          Evaluation detail
        </h2>

        <div className="mb-5">
          <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-ink-secondary">
            Input
          </h3>
          <pre className="max-h-50 overflow-y-auto whitespace-pre-wrap wrap-break-word rounded-md bg-bg-inset px-4 py-3 font-mono text-xs">
            {formatValue(entry.input)}
          </pre>
        </div>

        <div className="mb-5">
          <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-ink-secondary">
            Output
          </h3>
          <pre className="max-h-50 overflow-y-auto whitespace-pre-wrap wrap-break-word rounded-md bg-bg-inset px-4 py-3 font-mono text-xs">
            {formatValue(entry.output)}
          </pre>
        </div>

        {entry.expectedOutput != null && (
          <div className="mb-5">
            <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-ink-secondary">
              Expected Output
            </h3>
            <pre className="max-h-50 overflow-y-auto whitespace-pre-wrap wrap-break-word rounded-md bg-bg-inset px-4 py-3 font-mono text-xs">
              {formatValue(entry.expectedOutput)}
            </pre>
          </div>
        )}

        <div className="mb-5">
          <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-ink-secondary">
            Evaluations
          </h3>
          {entry.evaluations.map((ev, i) => {
            if (isPendingEvaluation(ev)) {
              return (
                <div
                  key={i}
                  className="mb-3 rounded-sm border-l-3 border-info px-3 py-2"
                >
                  <div className="mb-1 flex items-center gap-3">
                    <span className="inline-flex items-center gap-1 rounded-pill border border-info-border bg-info-bg px-3 py-1 text-xs font-bold tracking-wide text-info">
                      <svg
                        className="h-3 w-3"
                        viewBox="0 0 16 16"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <circle cx="8" cy="8" r="6.25" />
                        <path d="M8 4.5V8l2.5 1.5" />
                      </svg>
                      {ev.evaluator}
                    </span>
                    <span className="rounded-pill bg-info px-2 py-0.5 text-xs font-bold text-white">
                      Pending
                    </span>
                  </div>
                  <p className="m-0 text-sm leading-relaxed text-ink-secondary">
                    {ev.criteria}
                  </p>
                </div>
              );
            }
            return (
              <div
                key={i}
                className="mb-3 rounded-sm border-l-3 border-border px-3 py-2"
              >
                <div className="mb-1 flex items-center gap-3">
                  <span
                    className={`inline-block rounded-pill border px-3 py-1 text-xs font-bold tracking-wide ${pillBaseClasses(scoreTier(ev.score))} ${pillOpenFillClasses(scoreTier(ev.score))}`}
                  >
                    {ev.evaluator}
                  </span>
                  <span className="font-mono text-sm font-semibold">
                    {ev.score.toFixed(2)}
                  </span>
                </div>
                <p className="m-0 text-sm leading-relaxed text-ink-secondary">
                  {ev.reasoning}
                </p>
              </div>
            );
          })}
        </div>

        {(entry.analysisSummary || entry.analysis) && (
          <div className="mb-5">
            <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-ink-secondary">
              Entry Analysis
            </h3>
            <AnalysisBlock
              summary={entry.analysisSummary}
              detail={entry.analysis}
              title=""
            />
          </div>
        )}
      </div>
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────────

function formatLocalTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

function computeDuration(start: string, end: string): string {
  try {
    const ms = new Date(end).getTime() - new Date(start).getTime();
    if (ms < 1000) return `${ms}ms`;
    const secs = Math.round(ms / 1000);
    if (secs < 60) return `${secs}s`;
    const mins = Math.floor(secs / 60);
    const remSecs = secs % 60;
    return `${mins}m ${remSecs}s`;
  } catch {
    return "";
  }
}

function summarizeInput(input: unknown): string {
  if (typeof input === "string") {
    return input.length > 80 ? input.slice(0, 80) + "…" : input;
  }
  const s = JSON.stringify(input);
  return s.length > 80 ? s.slice(0, 80) + "…" : s;
}

function formatValue(value: unknown): string {
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}
