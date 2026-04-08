/** Datasets panel — sidebar list + table viewer */

import { useState, useEffect } from "react";
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
        const items = (Array.isArray(rawItems) ? rawItems : []) as DatasetItem[];
        const name = typeof raw.name === "string"
          ? raw.name
          : selected.replace(/^datasets\//, "").replace(/\.json$/, "");
        setData({ name, items });
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

function DatasetTable({ data }: { data: DatasetData }) {
  if (!data.items || data.items.length === 0) {
    return (
      <div className="flex h-full items-center justify-center font-sans text-base text-ink-muted">
        Dataset is empty
      </div>
    );
  }

  // Derive columns from keys of first item
  const allKeys = new Set<string>();
  for (const item of data.items) {
    for (const key of Object.keys(item)) {
      allKeys.add(key);
    }
  }
  const columns = Array.from(allKeys);

  return (
    <div className="p-6">
      <div className="mb-4 flex items-baseline gap-3">
        <span className="font-mono text-lg font-bold">{data.name}</span>
        <span className="font-sans text-sm text-ink-secondary">
          {data.items.length} items
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse font-sans text-sm">
          <thead>
            <tr>
              <th className="whitespace-nowrap border-b-2 border-border bg-surface-hover p-2 text-left text-xs font-semibold uppercase tracking-wider text-ink-secondary">
                #
              </th>
              {columns.map((col) => (
                <th
                  key={col}
                  className="whitespace-nowrap border-b-2 border-border bg-surface-hover p-2 text-left text-xs font-semibold uppercase tracking-wider text-ink-secondary"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.items.map((item, idx) => (
              <tr key={idx} className="hover:bg-surface-hover">
                <td className="w-8 border-b border-border p-2 font-mono text-xs text-ink-muted">
                  {idx + 1}
                </td>
                {columns.map((col) => (
                  <td
                    key={col}
                    className="max-w-100 border-b border-border p-2 align-top"
                  >
                    <CellValue value={item[col]} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CellValue({ value }: { value: unknown }) {
  if (value === null || value === undefined) {
    return <span className="text-ink-muted">—</span>;
  }
  if (typeof value === "string") {
    const truncated = value.length > 200 ? value.slice(0, 200) + "…" : value;
    return (
      <span className="whitespace-pre-wrap wrap-break-word">{truncated}</span>
    );
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return <span className="font-mono font-semibold">{String(value)}</span>;
  }
  // Object / array: render as compact JSON
  const json = JSON.stringify(value, null, 1);
  const truncated = json.length > 300 ? json.slice(0, 300) + "…" : json;
  return (
    <pre className="max-h-30 overflow-y-auto whitespace-pre-wrap wrap-break-word rounded-sm bg-bg-inset px-2 py-1 font-mono text-xs">
      {truncated}
    </pre>
  );
}
