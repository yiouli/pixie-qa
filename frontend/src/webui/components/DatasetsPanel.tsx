/** Datasets panel — sidebar list + structured table viewer */

import { useState, useEffect, useCallback } from "react";
import JsonView from "react18-json-view";
import "react18-json-view/src/style.css";
import type { ArtifactEntry, DatasetData, DatasetItem } from "../types";
import { SidebarList } from "./SidebarList";

interface DatasetsPanelProps {
  datasets: ArtifactEntry[];
  autoSelect?: string | null;
}

export function DatasetsPanel({ datasets, autoSelect }: DatasetsPanelProps) {
  const [selected, setSelected] = useState<string | null>(
    datasets[0]?.path ?? null,
  );
  const [data, setData] = useState<DatasetData | null>(null);
  const [loading, setLoading] = useState(false);

  // Apply autoSelect when it changes OR when datasets first populate
  useEffect(() => {
    if (autoSelect && datasets.some((d) => d.path === autoSelect)) {
      setSelected(autoSelect);
    }
  }, [autoSelect, datasets]);

  useEffect(() => {
    if (
      selected &&
      !datasets.some((d) => d.path === selected) &&
      datasets.length > 0
    ) {
      setSelected(datasets[0].path);
    } else if (!selected && datasets.length > 0) {
      setSelected(datasets[0].path);
    }
  }, [datasets, selected]);

  useEffect(() => {
    if (!selected) {
      setData(null);
      return;
    }
    setLoading(true);
    fetch(`/api/file?path=${encodeURIComponent(selected)}`)
      .then((r) => r.json())
      .then((raw: Record<string, unknown>) => {
        // Normalise: dataset files may use "entries" instead of "items"
        const rawItems = raw.items ?? raw.entries ?? [];
        const items = (
          Array.isArray(rawItems) ? rawItems : []
        ) as DatasetItem[];
        const name =
          typeof raw.name === "string"
            ? raw.name
            : selected.replace(/^datasets\//, "").replace(/\.json$/, "");
        const defaultEvaluators = Array.isArray(raw.evaluators)
          ? (raw.evaluators as string[])
          : [];
        setData({ name, items, defaultEvaluators });
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [selected]);

  return (
    <div className="flex h-full">
      <aside className="w-60 min-w-60 overflow-y-auto border-r border-border bg-surface py-2">
        <SidebarList
          items={datasets}
          selected={selected}
          onSelect={setSelected}
          emptyMessage="No datasets yet"
        />
      </aside>
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="flex h-full items-center justify-center font-sans text-base text-ink-muted">
            Loading…
          </div>
        ) : data ? (
          <DatasetTable data={data} />
        ) : (
          <div className="flex h-full items-center justify-center font-sans text-base text-ink-muted">
            <p>Select a dataset to view</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────────

/** Expand evaluators for a single entry, replacing "..." with defaults. */
function expandEvaluators(
  rowEvaluators: string[] | undefined,
  defaults: string[],
): string[] {
  if (!rowEvaluators || rowEvaluators.length === 0) return [...defaults];
  const result: string[] = [];
  for (const name of rowEvaluators) {
    if (name.trim() === "...") {
      result.push(...defaults);
    } else {
      result.push(name);
    }
  }
  return result;
}

/** Extract the short name from a filepath:name or module.Name evaluator reference. */
function shortName(ref: string): string {
  if (ref.includes(":")) return ref.split(":").pop()!;
  const last = ref.split(".").pop();
  return last || ref;
}

// ── DatasetTable ──────────────────────────────────────────────────

function DatasetTable({ data }: { data: DatasetData }) {
  const [detailItem, setDetailItem] = useState<DatasetItem | null>(null);

  if (!data.items || data.items.length === 0) {
    return (
      <div className="flex h-full items-center justify-center font-sans text-base text-ink-muted">
        Dataset is empty
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-4 flex items-baseline gap-3">
        <span className="font-mono text-lg font-bold">{data.name}</span>
        <span className="font-sans text-sm text-ink-secondary">
          {data.items.length} entries
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse font-sans text-sm">
          <thead>
            <tr>
              <th className="whitespace-nowrap border-b-2 border-border bg-surface-hover p-2 text-left text-xs font-semibold uppercase tracking-wider text-ink-secondary">
                #
              </th>
              <th className="whitespace-nowrap border-b-2 border-border bg-surface-hover p-2 text-left text-xs font-semibold uppercase tracking-wider text-ink-secondary">
                Description
              </th>
              <th className="whitespace-nowrap border-b-2 border-border bg-surface-hover p-2 text-left text-xs font-semibold uppercase tracking-wider text-ink-secondary">
                Eval Input
              </th>
              <th className="whitespace-nowrap border-b-2 border-border bg-surface-hover p-2 text-left text-xs font-semibold uppercase tracking-wider text-ink-secondary">
                Expectation
              </th>
              <th className="whitespace-nowrap border-b-2 border-border bg-surface-hover p-2 text-left text-xs font-semibold uppercase tracking-wider text-ink-secondary">
                Evaluators
              </th>
              <th className="whitespace-nowrap border-b-2 border-border bg-surface-hover p-2 text-left text-xs font-semibold uppercase tracking-wider text-ink-secondary">
                Details
              </th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((item, idx) => (
              <tr key={idx} className="hover:bg-surface-hover">
                <td className="w-8 border-b border-border p-2 font-mono text-xs text-ink-muted">
                  {idx + 1}
                </td>
                <td className="max-w-60 border-b border-border p-2 align-top">
                  <span className="whitespace-pre-wrap wrap-break-word text-sm">
                    {item.description ?? "—"}
                  </span>
                </td>
                <td className="max-w-80 border-b border-border p-2 align-top">
                  <div className="overflow-x-auto rounded-sm bg-bg-inset px-2 py-1">
                    <JsonView
                      src={item.eval_input}
                      collapsed={2}
                      collapseStringMode="address"
                      collapseStringsAfterLength={80}
                      theme="default"
                      enableClipboard={false}
                    />
                  </div>
                </td>
                <td className="max-w-80 border-b border-border p-2 align-top">
                  <ExpectationCell value={item.expectation} />
                </td>
                <td className="max-w-60 border-b border-border p-2 align-top">
                  <EvaluatorPills
                    evaluators={expandEvaluators(
                      item.evaluators,
                      data.defaultEvaluators,
                    )}
                  />
                </td>
                <td className="border-b border-border p-2 align-top">
                  <button
                    type="button"
                    className="border-none bg-transparent p-0 text-sm text-accent underline hover:text-accent-hover"
                    onClick={() => setDetailItem(item)}
                  >
                    details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {detailItem && (
        <EntryDetailModal
          item={detailItem}
          defaultEvaluators={data.defaultEvaluators}
          onClose={() => setDetailItem(null)}
        />
      )}
    </div>
  );
}

// ── Cell Renderers ──────────────────────────────────────────────────

function ExpectationCell({ value }: { value: unknown }) {
  if (value === null || value === undefined) {
    return <span className="text-ink-muted">—</span>;
  }
  if (typeof value === "string") {
    const truncated = value.length > 200 ? value.slice(0, 200) + "…" : value;
    return (
      <span className="whitespace-pre-wrap wrap-break-word text-sm">
        {truncated}
      </span>
    );
  }
  // Non-string values (arrays, objects): use json view
  return (
    <div className="overflow-x-auto rounded-sm bg-bg-inset px-2 py-1">
      <JsonView
        src={value}
        collapsed={1}
        collapseStringMode="address"
        collapseStringsAfterLength={80}
        theme="default"
        enableClipboard={false}
      />
    </div>
  );
}

function EvaluatorPills({ evaluators }: { evaluators: string[] }) {
  if (evaluators.length === 0) {
    return <span className="text-ink-muted">—</span>;
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {evaluators.map((name, i) => (
        <span
          key={i}
          className="inline-block rounded-pill border border-accent/40 px-2.5 py-0.5 text-xs font-medium text-accent"
          title={name}
        >
          {shortName(name)}
        </span>
      ))}
    </div>
  );
}

// ── Entry Detail Modal ──────────────────────────────────────────────────

function EntryDetailModal({
  item,
  defaultEvaluators,
  onClose,
}: {
  item: DatasetItem;
  defaultEvaluators: string[];
  onClose: () => void;
}) {
  const handleKey = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [handleKey]);

  const evaluators = expandEvaluators(item.evaluators, defaultEvaluators);

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
        <h2 className="mb-4 font-mono text-base font-bold">Entry detail</h2>

        {item.description && (
          <DetailSection title="Description">
            <p className="m-0 text-sm">{item.description}</p>
          </DetailSection>
        )}

        {item.input_data && (
          <DetailSection title="Input Data">
            <div className="rounded-md bg-bg-inset px-4 py-3">
              <JsonView
                src={item.input_data}
                collapseStringMode="address"
                collapsed={3}
                collapseStringsAfterLength={120}
                theme="default"
                enableClipboard={false}
              />
            </div>
          </DetailSection>
        )}

        {item.eval_input && (
          <DetailSection title="Eval Input">
            <div className="rounded-md bg-bg-inset px-4 py-3">
              <JsonView
                src={item.eval_input}
                collapseStringMode="address"
                collapsed={3}
                collapseStringsAfterLength={120}
                theme="default"
                enableClipboard={false}
              />
            </div>
          </DetailSection>
        )}

        {item.expectation !== undefined && item.expectation !== null && (
          <DetailSection title="Expectation">
            {typeof item.expectation === "string" ? (
              <p className="m-0 whitespace-pre-wrap wrap-break-word text-sm">
                {item.expectation}
              </p>
            ) : (
              <div className="rounded-md bg-bg-inset px-4 py-3">
                <JsonView
                  src={item.expectation}
                  collapseStringMode="address"
                  collapsed={3}
                  collapseStringsAfterLength={120}
                  theme="default"
                  enableClipboard={false}
                />
              </div>
            )}
          </DetailSection>
        )}

        {item.eval_metadata && (
          <DetailSection title="Eval Metadata">
            <div className="rounded-md bg-bg-inset px-4 py-3">
              <JsonView
                src={item.eval_metadata}
                collapseStringMode="address"
                collapsed={3}
                collapseStringsAfterLength={120}
                theme="default"
                enableClipboard={false}
              />
            </div>
          </DetailSection>
        )}

        <DetailSection title="Evaluators">
          <EvaluatorPills evaluators={evaluators} />
        </DetailSection>
      </div>
    </div>
  );
}

function DetailSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-5">
      <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-ink-secondary">
        {title}
      </h3>
      {children}
    </div>
  );
}
