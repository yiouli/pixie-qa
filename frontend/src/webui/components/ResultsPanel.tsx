/** Results panel — sidebar list + result viewer */

import { useState, useEffect, useRef } from "react";
import type {
  ArtifactEntry,
  TestResultData,
  DatasetResultData,
  EntryResultData,
  EvaluationResultData,
} from "../types";
import { SidebarList } from "./SidebarList";

interface ResultsPanelProps {
  results: ArtifactEntry[];
  autoSelect?: string | null;
  version?: number;
}

export function ResultsPanel({ results, autoSelect, version }: ResultsPanelProps) {
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

// ── Test Overview ──────────────────────────────────────────────────

function ResultView({ data }: { data: TestResultData }) {
  const { meta, datasets } = data;

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
      </div>

      {datasets.map((ds) => (
        <DatasetSection key={ds.dataset} dataset={ds} />
      ))}
    </div>
  );
}

// ── Per-Dataset Section ──────────────────────────────────────────────

function DatasetSection({ dataset }: { dataset: DatasetResultData }) {
  const passed = dataset.entries.filter((e) =>
    e.evaluations.every((ev) => ev.score >= SCORE_FAIL_THRESHOLD),
  ).length;
  const total = dataset.entries.length;
  const allPass = passed === total;

  return (
    <section className="mb-5 rounded-lg border border-border bg-surface p-6 shadow-sm">
      <div className="mb-4 flex items-center gap-3">
        <h2 className="font-mono text-lg font-bold">{dataset.dataset}</h2>
        <span
          className={`text-xl font-bold ${allPass ? "text-pass" : "text-fail"}`}
        >
          {passed}/{total} passed
        </span>
      </div>

      {/* Analysis section */}
      <div className="mb-5 rounded-md border-l-3 border-accent bg-bg-inset px-5 py-4">
        <h3 className="mb-3 text-sm font-semibold text-ink-secondary">
          Analysis &amp; Recommendations
        </h3>
        {dataset.analysis ? (
          <div
            className="analysis-content text-sm leading-relaxed"
            dangerouslySetInnerHTML={{
              __html: simpleMarkdown(dataset.analysis),
            }}
          />
        ) : (
          <div className="text-sm text-ink-muted">No analysis yet.</div>
        )}
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

/** Tailwind classes for pill border/bg/text by tier. */
function pillClasses(tier: ScoreTier): string {
  switch (tier) {
    case "pass":
      return "border-pass-border bg-pass-bg text-pass";
    case "warn":
      return "border-warn-border bg-warn-bg text-warn";
    case "fail":
      return "border-fail-border bg-fail-bg text-fail";
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

function EvalPill({ evaluation }: { evaluation: EvaluationResultData }) {
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

  const tier = scoreTier(evaluation.score);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        className={`inline-block cursor-pointer rounded-pill border px-3 py-1 text-xs font-bold tracking-wide transition-opacity hover:opacity-80 ${pillClasses(tier)}`}
        onClick={() => setOpen(!open)}
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
  const allPass = entry.evaluations.every((ev) => ev.score >= SCORE_FAIL_THRESHOLD);
  const hasWarning = allPass && entry.evaluations.some((ev) => ev.score <= SCORE_WARN_THRESHOLD);

  const description = entry.description || summarizeInput(entry.input);

  // Sort evaluations by score ascending
  const sortedEvals = [...entry.evaluations].sort((a, b) => a.score - b.score);

  // Row-level badge: FAIL > WARN > PASS
  const rowTier: ScoreTier = !allPass ? "fail" : hasWarning ? "warn" : "pass";

  return (
    <>
      <tr className={rowTier === "fail" ? "bg-fail-bg" : rowTier === "warn" ? "bg-warn-bg" : "bg-transparent"}>
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
            {sortedEvals.map((ev, i) => (
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
          {entry.evaluations.map((ev, i) => (
            <div
              key={i}
              className="mb-3 rounded-sm border-l-3 border-border px-3 py-2"
            >
              <div className="mb-1 flex items-center gap-3">
                <span
                  className={`inline-block rounded-pill border px-3 py-1 text-xs font-bold tracking-wide ${pillClasses(scoreTier(ev.score))}`}
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
          ))}
        </div>
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

function simpleMarkdown(md: string): string {
  // Minimal markdown to HTML: headers, bold, paragraphs, lists
  return md
    .replace(/^### (.+)$/gm, "<h4>$1</h4>")
    .replace(/^## (.+)$/gm, "<h3>$1</h3>")
    .replace(/^# (.+)$/gm, "<h2>$1</h2>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>\n?)+/g, "<ul>$&</ul>")
    .replace(/\n\n/g, "<br/><br/>")
    .replace(/\n/g, "<br/>");
}
