/** Results panel — sidebar list + result viewer */

import { useState, useEffect } from "react";
import type {
  ArtifactEntry,
  TestResultData,
  DatasetResultData,
  EntryResultData,
} from "../types";
import { SidebarList } from "./SidebarList";

interface ResultsPanelProps {
  results: ArtifactEntry[];
  autoSelect?: string | null;
}

export function ResultsPanel({ results, autoSelect }: ResultsPanelProps) {
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
  }, [selected]);

  return (
    <div className="split-panel">
      <aside className="split-sidebar">
        <SidebarList
          items={results}
          selected={selected}
          onSelect={setSelected}
          emptyMessage="No test results yet"
        />
      </aside>
      <div className="split-main result-viewer">
        {resultData ? (
          <ResultView data={resultData} />
        ) : (
          <div className="empty-state">
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
    <div className="result-view">
      <div className="result-overview">
        <h2>Test Overview</h2>
        <table className="overview-table">
          <tbody>
            <tr>
              <td className="label">Command</td>
              <td>
                <code>{meta.command}</code>
              </td>
            </tr>
            <tr>
              <td className="label">Start Time</td>
              <td>{startedAt}</td>
            </tr>
            <tr>
              <td className="label">End Time</td>
              <td>{endedAt}</td>
            </tr>
            <tr>
              <td className="label">Duration</td>
              <td>{duration}</td>
            </tr>
          </tbody>
        </table>

        <table className="dataset-summary-table">
          <thead>
            <tr>
              <th>Dataset</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            {datasets.map((ds) => {
              const passed = ds.entries.filter((e) =>
                e.evaluations.every((ev) => ev.score >= 0.5),
              ).length;
              return (
                <tr key={ds.dataset}>
                  <td>{ds.dataset}</td>
                  <td>
                    <span
                      className={`result-badge ${passed === ds.entries.length ? "pass" : "fail"}`}
                    >
                      {passed}/{ds.entries.length} passed
                    </span>
                  </td>
                </tr>
              );
            })}
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
    e.evaluations.every((ev) => ev.score >= 0.5),
  ).length;
  const total = dataset.entries.length;

  return (
    <section className="dataset-section">
      <h2>
        {dataset.dataset}{" "}
        <span className={`result-badge ${passed === total ? "pass" : "fail"}`}>
          {passed}/{total} passed
        </span>
      </h2>
      <div className="analysis-section">
        <h3>Analysis & Recommendations</h3>
        {dataset.analysis ? (
          <div
            className="analysis-content"
            dangerouslySetInnerHTML={{
              __html: simpleMarkdown(dataset.analysis),
            }}
          />
        ) : (
          <div>No analysis yet.</div>
        )}
      </div>
      <table className="entries-table">
        <thead>
          <tr>
            <th>Scenario</th>
            <th>Result</th>
            <th>Evaluations</th>
            <th>Details</th>
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

// ── Entry Row ──────────────────────────────────────────────────

function EntryRow({ entry }: { entry: EntryResultData }) {
  const [detailOpen, setDetailOpen] = useState(false);
  const allPass = entry.evaluations.every((ev) => ev.score >= 0.5);

  const description = entry.description || summarizeInput(entry.input);

  // Sort evaluations by score ascending
  const sortedEvals = [...entry.evaluations].sort((a, b) => a.score - b.score);

  return (
    <>
      <tr className={allPass ? "row-pass" : "row-fail"}>
        <td className="scenario-cell">{description}</td>
        <td>
          <span className={`pill ${allPass ? "pass" : "fail"}`}>
            {allPass ? "Pass" : "Fail"}
          </span>
        </td>
        <td className="evals-cell">
          {sortedEvals.map((ev, i) => (
            <span
              key={i}
              className={`eval-pill ${ev.score >= 0.5 ? "pass" : "fail"}`}
              title={`${ev.evaluator}: ${ev.score.toFixed(2)}`}
            >
              {ev.evaluator}
            </span>
          ))}
        </td>
        <td>
          <button
            type="button"
            className="link-btn"
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
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-card eval-detail-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <button type="button" className="modal-close" onClick={onClose}>
          ✕
        </button>
        <h2>Evaluation detail</h2>

        <div className="detail-section">
          <h3>Input</h3>
          <pre className="detail-pre">{formatValue(entry.input)}</pre>
        </div>

        <div className="detail-section">
          <h3>Output</h3>
          <pre className="detail-pre">{formatValue(entry.output)}</pre>
        </div>

        {entry.expectedOutput != null && (
          <div className="detail-section">
            <h3>Expected Output</h3>
            <pre className="detail-pre">
              {formatValue(entry.expectedOutput)}
            </pre>
          </div>
        )}

        <div className="detail-section">
          <h3>Evaluations</h3>
          {entry.evaluations.map((ev, i) => (
            <div key={i} className="eval-detail-item">
              <div className="eval-detail-header">
                <span
                  className={`eval-pill ${ev.score >= 0.5 ? "pass" : "fail"}`}
                >
                  {ev.evaluator}
                </span>
                <span className="eval-score">{ev.score.toFixed(2)}</span>
              </div>
              <p className="eval-reasoning">{ev.reasoning}</p>
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
